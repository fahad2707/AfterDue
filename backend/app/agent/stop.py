from app.domain.enums import ActionType, StopReason
from app.domain.policy import PolicyDecision
from app.models.documents import Customer, RecoveryCase
from app.simulator.costs import consumes_budget


def stop_before_action(
    *,
    case: RecoveryCase,
    customer: Customer,
    decision: PolicyDecision,
    recommended: ActionType,
    incremental_ev_paise: int | None,
    max_attempts: int,
    hard_cap: int,
    budget_remaining: int,
) -> StopReason | None:
    _ = customer, decision
    if case.status.value != "open":
        return StopReason.CASE_CLOSED
    if case.attempt_count >= max_attempts:
        return StopReason.MAX_ATTEMPTS_REACHED
    if case.attempt_count >= hard_cap:
        return StopReason.HARD_ITERATION_CAP
    automated = {
        ActionType.SEND_PAYMENT_LINK,
        ActionType.ATTEMPT_MANUAL_CHARGE,
    }
    if (
        recommended in automated
        and incremental_ev_paise is not None
        and incremental_ev_paise <= 0
    ):
        return StopReason.NEGATIVE_OR_ZERO_EV
    if consumes_budget(recommended) and budget_remaining <= 0:
        return StopReason.BUDGET_EXHAUSTED
    return None
