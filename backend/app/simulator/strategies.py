"""Baseline strategies.

They receive CaseView + an intervention budget. They do not import the oracle.
They do not receive latent_payment_intent. A leak would invalidate the
experiment; the import graph is the first line of defence.
"""

from collections.abc import Sequence
from dataclasses import dataclass

from app.domain.enums import ActionType
from app.simulator.costs import consumes_budget

# rule_based score weights. Documented in docs/evaluation.md.
BACKLOG_WEIGHT = 1
RECENT_REACTIVATION_BONUS = 50_000
HISTORICAL_SUCCESS_WEIGHT = 100_000
RECENT_REACTIVATION_DAYS = 45


@dataclass(frozen=True)
class CaseView:
    """Decision-time information. Anything hidden from the model stays out."""

    case_id: str
    #: Seed-stable key when present; used only for deterministic ordering.
    synthetic_case_key: str
    backlog_amount_paise: int
    invoice_count: int
    halt_duration_days: int
    days_since_reactivation: int
    card_type: str
    risk_flags: tuple[str, ...]
    historical_payment_success_rate: float
    previous_failure_count: int
    previous_halt_count: int
    subscription_age_days: int
    plan_amount_paise: int
    mandate_max_amount_paise: int
    has_dispute: bool
    customer_opted_out: bool
    allowed_actions: tuple[ActionType, ...]
    requires_escalation: bool
    stop: bool


@dataclass(frozen=True)
class CaseAction:
    case_id: str
    action: ActionType


def _pick_action(view: CaseView, budget_left: int) -> ActionType:
    allowed = set(view.allowed_actions)
    if ActionType.SEND_PAYMENT_LINK in allowed and budget_left > 0:
        return ActionType.SEND_PAYMENT_LINK
    if ActionType.ATTEMPT_MANUAL_CHARGE in allowed and budget_left > 0:
        return ActionType.ATTEMPT_MANUAL_CHARGE
    if view.requires_escalation or view.stop:
        if ActionType.ESCALATE_TO_MERCHANT in allowed:
            return ActionType.ESCALATE_TO_MERCHANT
    if ActionType.NO_ACTION in allowed:
        return ActionType.NO_ACTION
    # Policy always leaves NO_ACTION; this is a belt.
    return ActionType.NO_ACTION


def _apply(
    ordered: Sequence[CaseView], budget: int
) -> list[CaseAction]:
    remaining = budget
    chosen: list[CaseAction] = []
    for view in ordered:
        action = _pick_action(view, remaining)
        if action not in view.allowed_actions:
            action = ActionType.NO_ACTION
        if consumes_budget(action):
            remaining -= 1
        chosen.append(CaseAction(view.case_id, action))
    return chosen


class NaiveStrategy:
    """Stable case_id order. First eligible automated action wins."""

    name = "naive"

    def choose_actions(
        self, cases: Sequence[CaseView], intervention_budget: int
    ) -> list[CaseAction]:
        ordered = sorted(cases, key=lambda c: c.synthetic_case_key or c.case_id)
        return _apply(ordered, intervention_budget)


def rule_based_score(view: CaseView) -> int:
    recent = 1 if view.days_since_reactivation <= RECENT_REACTIVATION_DAYS else 0
    return (
        BACKLOG_WEIGHT * view.backlog_amount_paise
        + RECENT_REACTIVATION_BONUS * recent
        + int(HISTORICAL_SUCCESS_WEIGHT * view.historical_payment_success_rate)
    )


class RuleBasedStrategy:
    """Largest transparent score first, then the same action rule as naive."""

    name = "rule_based"

    def choose_actions(
        self, cases: Sequence[CaseView], intervention_budget: int
    ) -> list[CaseAction]:
        ordered = sorted(
            cases, key=lambda c: (-rule_based_score(c), c.synthetic_case_key or c.case_id)
        )
        return _apply(ordered, intervention_budget)


STRATEGIES = {
    NaiveStrategy.name: NaiveStrategy,
    RuleBasedStrategy.name: RuleBasedStrategy,
}
