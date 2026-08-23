"""Policy types and the pure evaluator.

The engine never reads the clock, the database, or settings. Every input
that could change a decision — including `now` — is on the context. That is
what makes the cooldown tests deterministic and the dry-run endpoint honest.
"""

from collections.abc import Sequence
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.domain.enums import (
    ActionType,
    CardType,
    PolicyReasonCode,
    Provenance,
)

POLICY_VERSION = "v1"

#: Starting set before any rule subtracts. NO_ACTION is always present after
#: evaluation because no rule is allowed to block doing nothing.
DEFAULT_ACTIONS: tuple[ActionType, ...] = (
    ActionType.NO_ACTION,
    ActionType.SEND_PAYMENT_LINK,
    ActionType.ATTEMPT_MANUAL_CHARGE,
    ActionType.ESCALATE_TO_MERCHANT,
)

AUTOMATED_COLLECTION: frozenset[ActionType] = frozenset(
    {ActionType.SEND_PAYMENT_LINK, ActionType.ATTEMPT_MANUAL_CHARGE}
)
CONTACT_ACTIONS: frozenset[ActionType] = frozenset({ActionType.SEND_PAYMENT_LINK})


class PolicyContext(BaseModel):
    model_config = ConfigDict(extra="forbid")

    case_id: str
    card_type: CardType
    backlog_amount_paise: int = Field(ge=0)
    mandate_max_amount_paise: int = Field(ge=0)
    risk_flags: list[str] = Field(default_factory=list)
    has_dispute: bool = False
    customer_opted_out: bool = False
    attempt_count: int = Field(default=0, ge=0)
    last_contact_at: datetime | None = None
    now: datetime
    max_attempts: int = Field(default=3, ge=1)
    contact_cooldown_hours: int = Field(default=24, ge=0)


class AppliedRule(BaseModel):
    rule_id: str
    reason_code: PolicyReasonCode
    provenance: Provenance
    source_url: str | None
    blocked_actions: list[ActionType]
    requires_escalation: bool = False
    stop: bool = False


class RuleHit:
    """Internal evaluator result. Not an API shape."""

    __slots__ = (
        "rule_id",
        "reason_code",
        "provenance",
        "source_url",
        "blocked_actions",
        "requires_escalation",
        "stop",
    )

    def __init__(
        self,
        *,
        rule_id: str,
        reason_code: PolicyReasonCode,
        provenance: Provenance,
        blocked_actions: frozenset[ActionType],
        source_url: str | None = None,
        requires_escalation: bool = False,
        stop: bool = False,
    ) -> None:
        self.rule_id = rule_id
        self.reason_code = reason_code
        self.provenance = provenance
        self.source_url = source_url
        self.blocked_actions = blocked_actions
        self.requires_escalation = requires_escalation
        self.stop = stop

    def as_applied(self) -> AppliedRule:
        return AppliedRule(
            rule_id=self.rule_id,
            reason_code=self.reason_code,
            provenance=self.provenance,
            source_url=self.source_url,
            blocked_actions=sorted(self.blocked_actions, key=lambda a: a.value),
            requires_escalation=self.requires_escalation,
            stop=self.stop,
        )


class PolicyDecision(BaseModel):
    policy_version: str
    allowed_actions: list[ActionType]
    blocked_actions: list[ActionType]
    reason_codes: list[PolicyReasonCode]
    requires_escalation: bool
    stop: bool
    applied_rules: list[AppliedRule] = Field(default_factory=list)


def evaluate_policy(
    context: PolicyContext,
    rules: Sequence = (),
    *,
    version: str = POLICY_VERSION,
) -> PolicyDecision:
    """Intersect every applicable rule onto the default action set.

    Evaluation does not abort after the first hit. A terminal STOP (dispute)
    still lets later rules contribute their reason codes, so a case that is
    both in dispute and over the mandate cap reports both facts.
    """
    allowed = set(DEFAULT_ACTIONS)
    blocked: set[ActionType] = set()
    applied: list[AppliedRule] = []
    reason_codes: list[PolicyReasonCode] = []
    requires_escalation = False
    stop = False

    for rule in rules:
        hit = rule(context)
        if hit is None:
            continue
        blocked |= hit.blocked_actions
        allowed -= hit.blocked_actions
        applied.append(hit.as_applied())
        reason_codes.append(hit.reason_code)
        requires_escalation = requires_escalation or hit.requires_escalation
        stop = stop or hit.stop

    # Doing nothing is always permitted. Escalation stays available when any
    # rule asked for it, even if a later rule was careless about the set.
    allowed.add(ActionType.NO_ACTION)
    if requires_escalation:
        allowed.add(ActionType.ESCALATE_TO_MERCHANT)
        blocked.discard(ActionType.ESCALATE_TO_MERCHANT)

    if stop:
        allowed -= AUTOMATED_COLLECTION
        blocked |= AUTOMATED_COLLECTION

    blocked.discard(ActionType.NO_ACTION)
    allowed -= blocked

    order = list(DEFAULT_ACTIONS)
    return PolicyDecision(
        policy_version=version,
        allowed_actions=[a for a in order if a in allowed],
        blocked_actions=[a for a in order if a in blocked],
        reason_codes=reason_codes,
        requires_escalation=requires_escalation,
        stop=stop,
        applied_rules=applied,
    )
