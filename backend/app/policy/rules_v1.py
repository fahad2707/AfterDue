"""Policy v1 rules.

Typed Python, not a YAML DSL. A homemade expression language would be harder
to test than the rules themselves and would hide the safety boundary in a
parser. Versioning is the `POLICY_VERSION` constant plus `policy_version` on
every decision and every recovery case.

No rule in this file is DOCUMENTED_PLATFORM_BEHAVIOR. We have not independently
verified the corresponding Razorpay pages, and inventing a source URL would be
worse than an honest assumption.
"""

from collections.abc import Callable, Sequence
from datetime import timedelta

from app.domain.enums import (
    ActionType,
    CardType,
    PolicyReasonCode,
    Provenance,
)
from app.domain.policy import (
    AUTOMATED_COLLECTION,
    CONTACT_ACTIONS,
    PolicyContext,
    RuleHit,
)

Rule = Callable[[PolicyContext], RuleHit | None]


def domestic_card(context: PolicyContext) -> RuleHit | None:
    if context.card_type is not CardType.DOMESTIC:
        return None
    return RuleHit(
        rule_id="domestic_card_no_manual_charge",
        reason_code=PolicyReasonCode.DOMESTIC_CARD_MANUAL_CHARGE_UNSUPPORTED,
        provenance=Provenance.PRODUCT_DESIGN_ASSUMPTION,
        source_url=None,
        blocked_actions=frozenset({ActionType.ATTEMPT_MANUAL_CHARGE}),
    )


def mandate_cap(context: PolicyContext) -> RuleHit | None:
    if context.backlog_amount_paise <= context.mandate_max_amount_paise:
        return None
    return RuleHit(
        rule_id="mandate_cap",
        reason_code=PolicyReasonCode.MANDATE_CAP_EXCEEDED,
        provenance=Provenance.PRODUCT_DESIGN_ASSUMPTION,
        source_url=None,
        blocked_actions=frozenset({ActionType.ATTEMPT_MANUAL_CHARGE}),
    )


def risk_flags(context: PolicyContext) -> RuleHit | None:
    if not context.risk_flags:
        return None
    return RuleHit(
        rule_id="risk_flag",
        reason_code=PolicyReasonCode.RISK_FLAG_PRESENT,
        provenance=Provenance.SAFETY_GUARDRAIL,
        source_url=None,
        blocked_actions=AUTOMATED_COLLECTION,
        requires_escalation=True,
    )


def active_dispute(context: PolicyContext) -> RuleHit | None:
    if not context.has_dispute:
        return None
    return RuleHit(
        rule_id="active_dispute",
        reason_code=PolicyReasonCode.ACTIVE_DISPUTE,
        provenance=Provenance.SAFETY_GUARDRAIL,
        source_url=None,
        blocked_actions=AUTOMATED_COLLECTION,
        requires_escalation=True,
        stop=True,
    )


def customer_opt_out(context: PolicyContext) -> RuleHit | None:
    if not context.customer_opted_out:
        return None
    return RuleHit(
        rule_id="customer_opt_out",
        reason_code=PolicyReasonCode.CUSTOMER_OPTED_OUT,
        provenance=Provenance.SAFETY_GUARDRAIL,
        source_url=None,
        blocked_actions=CONTACT_ACTIONS,
        requires_escalation=True,
    )


def max_attempts(context: PolicyContext) -> RuleHit | None:
    if context.attempt_count < context.max_attempts:
        return None
    return RuleHit(
        rule_id="max_attempts",
        reason_code=PolicyReasonCode.MAX_ATTEMPTS_REACHED,
        provenance=Provenance.SAFETY_GUARDRAIL,
        source_url=None,
        blocked_actions=AUTOMATED_COLLECTION,
        requires_escalation=True,
    )


def contact_cooldown(context: PolicyContext) -> RuleHit | None:
    if context.last_contact_at is None:
        return None
    elapsed = context.now - context.last_contact_at
    if elapsed >= timedelta(hours=context.contact_cooldown_hours):
        return None
    return RuleHit(
        rule_id="contact_cooldown",
        reason_code=PolicyReasonCode.CONTACT_COOLDOWN_ACTIVE,
        provenance=Provenance.SAFETY_GUARDRAIL,
        source_url=None,
        blocked_actions=CONTACT_ACTIONS,
    )


RULES_V1: Sequence[Rule] = (
    domestic_card,
    mandate_cap,
    risk_flags,
    active_dispute,
    customer_opt_out,
    max_attempts,
    contact_cooldown,
)

RULE_CATALOG = (
    {
        "rule_id": "domestic_card_no_manual_charge",
        "reason_code": PolicyReasonCode.DOMESTIC_CARD_MANUAL_CHARGE_UNSUPPORTED.value,
        "condition": "card_type == domestic",
        "effect": "block ATTEMPT_MANUAL_CHARGE; SEND_PAYMENT_LINK remains eligible",
        "provenance": Provenance.PRODUCT_DESIGN_ASSUMPTION.value,
        "source_url": None,
    },
    {
        "rule_id": "mandate_cap",
        "reason_code": PolicyReasonCode.MANDATE_CAP_EXCEEDED.value,
        "condition": "backlog_amount_paise > mandate_max_amount_paise",
        "effect": "block ATTEMPT_MANUAL_CHARGE",
        "provenance": Provenance.PRODUCT_DESIGN_ASSUMPTION.value,
        "source_url": None,
    },
    {
        "rule_id": "risk_flag",
        "reason_code": PolicyReasonCode.RISK_FLAG_PRESENT.value,
        "condition": "risk_flags is non-empty",
        "effect": "block automated collection; require escalation",
        "provenance": Provenance.SAFETY_GUARDRAIL.value,
        "source_url": None,
    },
    {
        "rule_id": "active_dispute",
        "reason_code": PolicyReasonCode.ACTIVE_DISPUTE.value,
        "condition": "has_dispute == true",
        "effect": "STOP automated recovery; allow only escalation / no_action",
        "provenance": Provenance.SAFETY_GUARDRAIL.value,
        "source_url": None,
    },
    {
        "rule_id": "customer_opt_out",
        "reason_code": PolicyReasonCode.CUSTOMER_OPTED_OUT.value,
        "condition": "customer_opted_out == true",
        "effect": "block SEND_PAYMENT_LINK; require escalation",
        "provenance": Provenance.SAFETY_GUARDRAIL.value,
        "source_url": None,
    },
    {
        "rule_id": "max_attempts",
        "reason_code": PolicyReasonCode.MAX_ATTEMPTS_REACHED.value,
        "condition": "attempt_count >= max_attempts",
        "effect": "block automated collection; require escalation",
        "provenance": Provenance.SAFETY_GUARDRAIL.value,
        "source_url": None,
    },
    {
        "rule_id": "contact_cooldown",
        "reason_code": PolicyReasonCode.CONTACT_COOLDOWN_ACTIVE.value,
        "condition": "now - last_contact_at < contact_cooldown_hours",
        "effect": "block SEND_PAYMENT_LINK",
        "provenance": Provenance.SAFETY_GUARDRAIL.value,
        "source_url": None,
    },
)
