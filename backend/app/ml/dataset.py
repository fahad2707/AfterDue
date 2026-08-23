"""Randomized synthetic training rows. No Mongo. No strategy assignment."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from random import Random

from app.domain.enums import ActionType, CardType
from app.domain.policy import PolicyContext
from app.policy import evaluate_v1
from app.simulator.config import SimulationConfig
from app.simulator.identity import synthetic_case_key, synthetic_customer_key
from app.simulator.oracle import OracleCase, OutcomeOracle
from app.simulator.population import Fate, SubscriberPlan, draw_population
from app.simulator.strategies import CaseView
from app.simulator.world import DECISION_NOW, ORIGIN

SCOREABLE: tuple[ActionType, ...] = (
    ActionType.NO_ACTION,
    ActionType.SEND_PAYMENT_LINK,
    ActionType.ATTEMPT_MANUAL_CHARGE,
)

DEFAULT_TRAIN_SIZE = 20_000


@dataclass(frozen=True)
class TrainingRow:
    group_id: str
    synthetic_case_key: str
    world_seed: int
    view: CaseView
    action: ActionType
    recovered: int


def _at(base: datetime, **delta) -> datetime:
    return base + timedelta(**delta)


def _observation(plan: SubscriberPlan, halt_ordinal: int) -> CaseView | None:
    if plan.fate is not Fate.REACTIVATED:
        return None
    if halt_ordinal == 2 and plan.halt_cycles < 2:
        return None
    created = _at(ORIGIN, days=plan.index)
    first_halt = _at(created, days=plan.halt_offset_days)
    if halt_ordinal == 1:
        halt_at = first_halt
        cycles = plan.missed_cycles
    else:
        halt_at = _at(first_halt, days=30 * plan.missed_cycles + 50)
        cycles = max(1, plan.missed_cycles // 2)
    reactivated = _at(halt_at, days=30 * cycles + 12)
    now = DECISION_NOW
    if now.tzinfo is None:
        now = now.replace(tzinfo=UTC)
    return CaseView(
        case_id=f"train_{synthetic_case_key(plan.index, halt_ordinal)}",
        synthetic_case_key=synthetic_case_key(plan.index, halt_ordinal),
        backlog_amount_paise=plan.plan_amount_paise * cycles,
        invoice_count=cycles,
        halt_duration_days=max(0, (reactivated - halt_at).days),
        days_since_reactivation=max(0, (now - reactivated).days),
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
        allowed_actions=(),
        requires_escalation=False,
        stop=False,
    )


def _with_policy(view: CaseView, now: datetime) -> CaseView:
    decision = evaluate_v1(
        PolicyContext(
            case_id=view.case_id,
            card_type=CardType(view.card_type),
            backlog_amount_paise=view.backlog_amount_paise,
            mandate_max_amount_paise=view.mandate_max_amount_paise,
            risk_flags=list(view.risk_flags),
            has_dispute=view.has_dispute,
            customer_opted_out=view.customer_opted_out,
            attempt_count=0,
            last_contact_at=None,
            now=now,
            max_attempts=3,
            contact_cooldown_hours=24,
        )
    )
    return CaseView(
        **{
            **view.__dict__,
            "allowed_actions": tuple(decision.allowed_actions),
            "requires_escalation": decision.requires_escalation,
            "stop": decision.stop,
        }
    )


def _world_seed(dataset_seed: int, index: int) -> int:
    return (dataset_seed * 1_000_003 + index * 9176) % 2_147_483_647


def generate_training_rows(
    dataset_seed: int,
    n_examples: int = DEFAULT_TRAIN_SIZE,
) -> list[TrainingRow]:
    """One randomized permitted action per synthetic case. Reproducible."""
    assign = Random(dataset_seed)
    rows: list[TrainingRow] = []
    world_index = 0
    now = DECISION_NOW
    while len(rows) < n_examples:
        seed = _world_seed(dataset_seed, world_index)
        world_index += 1
        config = SimulationConfig(subscriber_count=200, seed=seed)
        oracle = OutcomeOracle(seed)
        for plan in draw_population(config):
            for ordinal in (1, 2):
                raw = _observation(plan, ordinal)
                if raw is None:
                    continue
                view = _with_policy(raw, now)
                candidates = [a for a in view.allowed_actions if a in SCOREABLE]
                if not candidates:
                    candidates = [ActionType.NO_ACTION]
                action = assign.choice(candidates)
                outcome = oracle.decide(
                    OracleCase(
                        case_id=view.case_id,
                        synthetic_case_key=view.synthetic_case_key,
                        synthetic_customer_key=synthetic_customer_key(plan.index),
                        backlog_amount_paise=view.backlog_amount_paise,
                        historical_payment_success_rate=view.historical_payment_success_rate,
                        has_dispute=view.has_dispute,
                        customer_opted_out=view.customer_opted_out,
                    ),
                    action,
                )
                recovered = 1 if outcome.outcome == "paid" else 0
                rows.append(
                    TrainingRow(
                        group_id=f"{seed}:{view.synthetic_case_key}",
                        synthetic_case_key=view.synthetic_case_key,
                        world_seed=seed,
                        view=view,
                        action=action,
                        recovered=recovered,
                    )
                )
                if len(rows) >= n_examples:
                    return rows
    return rows
