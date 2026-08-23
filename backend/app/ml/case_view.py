"""Build a decision-time CaseView from persisted ledger entities."""

from datetime import datetime

from app.config import get_settings
from app.domain.policy import PolicyContext
from app.models.documents import Customer, RecoveryCase, Subscription
from app.policy import evaluate_v1
from app.simulator.strategies import CaseView
from app.simulator.world import DECISION_NOW


def build_case_view(
    case: RecoveryCase,
    customer: Customer,
    subscription: Subscription,
    *,
    now: datetime | None = None,
    max_attempts: int | None = None,
    contact_cooldown_hours: int | None = None,
) -> CaseView:
    settings = get_settings()
    decision_at = now or DECISION_NOW
    decision = evaluate_v1(
        PolicyContext(
            case_id=case.case_id,
            card_type=subscription.card_type,
            backlog_amount_paise=case.backlog_amount_paise,
            mandate_max_amount_paise=subscription.mandate_max_amount_paise,
            risk_flags=customer.risk_flags,
            has_dispute=customer.has_active_dispute,
            customer_opted_out=customer.customer_opted_out,
            attempt_count=case.attempt_count,
            last_contact_at=case.last_contact_at,
            now=decision_at,
            max_attempts=max_attempts or settings.policy_max_attempts,
            contact_cooldown_hours=contact_cooldown_hours
            if contact_cooldown_hours is not None
            else settings.policy_contact_cooldown_hours,
        )
    )
    return CaseView(
        case_id=case.case_id,
        synthetic_case_key=case.synthetic_case_key or case.case_id,
        backlog_amount_paise=case.backlog_amount_paise,
        invoice_count=case.invoice_count,
        halt_duration_days=case.halt_duration_days,
        days_since_reactivation=max(0, (decision_at - case.reactivated_at).days),
        card_type=subscription.card_type.value,
        risk_flags=tuple(customer.risk_flags),
        historical_payment_success_rate=customer.historical_payment_success_rate,
        previous_failure_count=customer.previous_failure_count,
        previous_halt_count=customer.previous_halt_count,
        subscription_age_days=customer.subscription_age_days,
        plan_amount_paise=subscription.plan_amount_paise,
        mandate_max_amount_paise=subscription.mandate_max_amount_paise,
        has_dispute=customer.has_active_dispute,
        customer_opted_out=customer.customer_opted_out,
        allowed_actions=tuple(decision.allowed_actions),
        requires_escalation=decision.requires_escalation,
        stop=decision.stop,
    )
