"""In-memory post-halt cases for evaluation.

Reuses the population draw, collectibility rules, and policy engine.
Does not write Mongo and does not go through RecoveryWindowService.
Timeline math matches `app.ml.dataset._observation` / world halt cycles.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta

from app.domain.enums import ActionType, ServiceDeliveryStatus
from app.domain.policy import PolicyContext
from app.policy import evaluate_v1
from app.simulator.config import SimulationConfig
from app.simulator.identity import synthetic_case_key, synthetic_customer_key
from app.simulator.oracle import OracleCase, latent_payment_intent
from app.simulator.population import Fate, SubscriberPlan, draw_population
from app.simulator.strategies import CaseView
from app.simulator.world import DECISION_NOW, ORIGIN


def _bucket_amounts(
    plan_amount_paise: int, delivery: tuple[ServiceDeliveryStatus, ...]
) -> tuple[int, int, int, int, int, int]:
    historical = 0
    collectible = 0
    excluded = 0
    review = 0
    collectible_invoices = 0
    for status in delivery:
        historical += plan_amount_paise
        if status is ServiceDeliveryStatus.DELIVERED:
            collectible += plan_amount_paise
            collectible_invoices += 1
        elif status is ServiceDeliveryStatus.SUSPENDED:
            excluded += plan_amount_paise
        else:
            review += plan_amount_paise
    return (
        historical,
        collectible,
        excluded,
        review,
        len(delivery),
        collectible_invoices,
    )


def _timeline(
    plan: SubscriberPlan, halt_ordinal: int
) -> tuple[object, object, tuple[ServiceDeliveryStatus, ...]]:
    created = ORIGIN + timedelta(days=plan.index)
    first_halt = created + timedelta(days=plan.halt_offset_days)
    if halt_ordinal == 1:
        halt_at = first_halt
        cycles = plan.missed_cycles
        delivery = plan.first_halt_delivery
    else:
        halt_at = first_halt + timedelta(days=30 * plan.missed_cycles + 50)
        cycles = max(1, plan.missed_cycles // 2)
        delivery = plan.second_halt_delivery
    reactivated = halt_at + timedelta(days=30 * cycles + 12)
    return halt_at, reactivated, delivery


def _view(
    *,
    case_id: str,
    synthetic_case_key: str,
    backlog_amount_paise: int,
    invoice_count: int,
    halt_duration_days: int,
    days_since_reactivation: int,
    plan: SubscriberPlan,
) -> CaseView:
    context = PolicyContext(
        case_id=case_id,
        card_type=plan.card_type,
        backlog_amount_paise=backlog_amount_paise,
        mandate_max_amount_paise=plan.plan_amount_paise,
        risk_flags=list(plan.risk_flags),
        has_dispute=plan.has_active_dispute,
        customer_opted_out=plan.customer_opted_out,
        attempt_count=0,
        last_contact_at=None,
        now=DECISION_NOW,
        max_attempts=3,
        contact_cooldown_hours=24,
    )
    decision = evaluate_v1(context)
    return CaseView(
        case_id=case_id,
        synthetic_case_key=synthetic_case_key,
        backlog_amount_paise=backlog_amount_paise,
        invoice_count=invoice_count,
        halt_duration_days=halt_duration_days,
        days_since_reactivation=days_since_reactivation,
        card_type=plan.card_type.value,
        risk_flags=plan.risk_flags,
        historical_payment_success_rate=plan.historical_payment_success_rate,
        previous_failure_count=plan.previous_failure_count,
        previous_halt_count=plan.previous_halt_count,
        subscription_age_days=plan.subscription_age_days,
        plan_amount_paise=plan.plan_amount_paise,
        mandate_max_amount_paise=plan.plan_amount_paise,
        has_dispute=plan.has_active_dispute,
        customer_opted_out=plan.customer_opted_out,
        allowed_actions=tuple(decision.allowed_actions),
        requires_escalation=decision.requires_escalation,
        stop=decision.stop,
    )


def unconstrained_preference(view: CaseView) -> ActionType:
    """What a naive collector would try if policy were ignored."""
    if view.stop or view.requires_escalation:
        return ActionType.ESCALATE_TO_MERCHANT
    return ActionType.SEND_PAYMENT_LINK


@dataclass(frozen=True)
class EvalCase:
    case_id: str
    synthetic_case_key: str
    synthetic_customer_key: str
    historical_unpaid_amount_paise: int
    collectible_amount_paise: int
    not_collectible_amount_paise: int
    review_required_amount_paise: int
    historical_invoice_count: int
    collectible_invoice_count: int
    latent_payment_intent: float
    families: tuple[str, ...]
    ungated_view: CaseView
    gated_view: CaseView | None
    oracle_case: OracleCase

    @property
    def invalid_amount_paise(self) -> int:
        return (
            self.not_collectible_amount_paise + self.review_required_amount_paise
        )


def build_eval_cases(config: SimulationConfig) -> list[EvalCase]:
    """Every reactivated halt episode with historical unpaid > 0."""
    plans = draw_population(config)
    cases: list[EvalCase] = []
    for plan in plans:
        if plan.fate is not Fate.REACTIVATED:
            continue
        ordinals = (1, 2) if plan.halt_cycles == 2 else (1,)
        for ordinal in ordinals:
            built = _one_case(config.seed, plan, ordinal)
            if built is not None:
                cases.append(built)
    cases.sort(key=lambda c: c.synthetic_case_key)
    return cases


def _one_case(seed: int, plan: SubscriberPlan, halt_ordinal: int) -> EvalCase | None:
    halt_at, reactivated, delivery = _timeline(plan, halt_ordinal)
    if not delivery:
        return None
    historical, collectible, excluded, review, n_hist, n_col = _bucket_amounts(
        plan.plan_amount_paise, delivery
    )
    if historical <= 0:
        return None
    if historical != collectible + excluded + review:
        raise RuntimeError("collectibility buckets must sum to historical unpaid")
    key = synthetic_case_key(plan.index, halt_ordinal)
    customer_key = synthetic_customer_key(plan.index)
    case_id = f"eval_{key}"
    halt_days = max(0, (reactivated - halt_at).days)
    since = max(0, (DECISION_NOW - reactivated).days)
    ungated = _view(
        case_id=case_id,
        synthetic_case_key=key,
        backlog_amount_paise=historical,
        invoice_count=n_hist,
        halt_duration_days=halt_days,
        days_since_reactivation=since,
        plan=plan,
    )
    gated = None
    if collectible > 0:
        gated = _view(
            case_id=case_id,
            synthetic_case_key=key,
            backlog_amount_paise=collectible,
            invoice_count=n_col,
            halt_duration_days=halt_days,
            days_since_reactivation=since,
            plan=plan,
        )
    oracle = OracleCase(
        case_id=case_id,
        synthetic_case_key=key,
        synthetic_customer_key=customer_key,
        backlog_amount_paise=collectible,
        historical_payment_success_rate=plan.historical_payment_success_rate,
        has_dispute=plan.has_active_dispute,
        customer_opted_out=plan.customer_opted_out,
    )
    latent = latent_payment_intent(seed, customer_key)
    from app.evaluation.scenarios import tag_families

    families = tag_families(
        collectible=collectible,
        historical=historical,
        excluded=excluded,
        review=review,
        gated=gated,
        ungated=ungated,
        latent=latent,
        historical_success=plan.historical_payment_success_rate,
        has_dispute=plan.has_active_dispute,
        opted_out=plan.customer_opted_out,
    )
    return EvalCase(
        case_id=case_id,
        synthetic_case_key=key,
        synthetic_customer_key=customer_key,
        historical_unpaid_amount_paise=historical,
        collectible_amount_paise=collectible,
        not_collectible_amount_paise=excluded,
        review_required_amount_paise=review,
        historical_invoice_count=n_hist,
        collectible_invoice_count=n_col,
        latent_payment_intent=latent,
        families=families,
        ungated_view=ungated,
        gated_view=gated,
        oracle_case=oracle,
    )


