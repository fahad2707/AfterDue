"""Simulation runner. World / policy / strategy / oracle / metrics stay separate."""

from datetime import UTC, datetime
from uuid import uuid4

from app.config import get_settings
from app.domain.enums import ActionType
from app.domain.policy import PolicyContext
from app.domain.time import utcnow
from app.models.documents import RecoveryCase
from app.models.simulation import SimulationRun, SimulationStatus
from app.policy import evaluate_v1
from app.repositories.customers import CustomerRepository
from app.repositories.recovery_cases import RecoveryCaseRepository
from app.repositories.simulation_runs import SimulationRunRepository
from app.repositories.subscriptions import SubscriptionRepository
from app.simulator.config import SimulationConfig
from app.simulator.costs import consumes_budget
from app.simulator.metrics import StrategyMetrics, aggregate_metrics
from app.simulator.oracle import OracleCase, OutcomeOracle
from app.simulator.strategies import (
    STRATEGIES,
    CaseView,
    NaiveStrategy,
    RuleBasedStrategy,
)
from app.simulator.world import DECISION_NOW, WorldGenerator, WorldSummary


def new_run_id(seed: int) -> str:
    stamp = datetime.now(UTC).strftime("%Y%m%d%H%M%S")
    return f"run_{seed}_{stamp}_{uuid4().hex[:6]}"


def _days_since(reactivated_at, now) -> int:
    return max(0, (now - reactivated_at).days)


class SimulationRunner:
    def __init__(
        self,
        runs: SimulationRunRepository,
        customers: CustomerRepository,
        subscriptions: SubscriptionRepository,
        cases: RecoveryCaseRepository,
        world: WorldGenerator,
    ) -> None:
        self.runs = runs
        self.customers = customers
        self.subscriptions = subscriptions
        self.cases = cases
        self.world = world

    async def generate(self, config: SimulationConfig) -> tuple[str, WorldSummary]:
        run_id = new_run_id(config.seed)
        record = SimulationRun(
            run_id=run_id,
            seed=config.seed,
            synthetic=True,
            config=config,
            status=SimulationStatus.CREATED,
            created_at=utcnow(),
        )
        await self.runs.create(record)
        try:
            _, summary = await self.world.generate(config, run_id)
            record.status = SimulationStatus.GENERATED
            record.world_summary = summary.__dict__
            await self.runs.save(record)
            return run_id, summary
        except Exception as exc:
            record.status = SimulationStatus.FAILED
            record.error = f"{type(exc).__name__}: {exc}"
            await self.runs.save(record)
            raise

    async def run_strategies(
        self, run_id: str, strategy_names: list[str]
    ) -> dict[str, StrategyMetrics]:
        record = await self.runs.get(run_id)
        if record is None:
            raise KeyError(run_id)
        config = record.config
        cases = await self.cases.list_by_run(run_id)
        views, oracle_cases, policies = await self._views(config, cases)
        case_ids = tuple(v.case_id for v in views)

        oracle = OutcomeOracle(config.seed)
        no_action = {
            oc.case_id: oracle.decide(oc, ActionType.NO_ACTION) for oc in oracle_cases
        }

        results: dict[str, StrategyMetrics] = {}
        for name in strategy_names:
            cls = STRATEGIES.get(name)
            if cls is None:
                raise ValueError(f"unknown strategy {name}")
            strategy = cls()
            actions = strategy.choose_actions(views, config.intervention_budget)
            acted_ids = {a.case_id for a in actions}
            if acted_ids != set(case_ids) or len(actions) != len(case_ids):
                raise RuntimeError(
                    f"{name} did not decide on the identical case set for {run_id}"
                )
            used = sum(1 for a in actions if consumes_budget(a.action))
            if used > config.intervention_budget:
                raise RuntimeError(f"{name} exceeded intervention budget")
            allowed_by_id = {v.case_id: v.allowed_actions for v in views}
            for action in actions:
                if action.action not in allowed_by_id[action.case_id]:
                    raise RuntimeError(
                        f"{name} chose {action.action} outside policy on {action.case_id}"
                    )
            by_id = {oc.case_id: oc for oc in oracle_cases}
            selected = {
                a.case_id: oracle.decide(by_id[a.case_id], a.action) for a in actions
            }
            results[name] = aggregate_metrics(
                strategy_name=name,
                budget=config.intervention_budget,
                views=views,
                actions=actions,
                selected=selected,
                no_action=no_action,
            )

        record.strategy_results = {
            name: metrics.__dict__ for name, metrics in results.items()
        }
        record.status = SimulationStatus.COMPLETED
        record.completed_at = utcnow()
        await self.runs.save(record)
        return results

    async def _views(
        self, config: SimulationConfig, cases: list[RecoveryCase]
    ):
        settings = get_settings()
        views: list[CaseView] = []
        oracle_cases: list[OracleCase] = []
        policies = []
        ordered = sorted(cases, key=lambda c: c.case_id)
        for case in ordered:
            customer = await self.customers.get(case.customer_id)
            subscription = await self.subscriptions.get(case.subscription_id)
            if customer is None or subscription is None:
                continue
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
                    now=DECISION_NOW,
                    max_attempts=config.max_attempts or settings.policy_max_attempts,
                    contact_cooldown_hours=config.contact_cooldown_hours,
                )
            )
            policies.append(decision)
            views.append(
                CaseView(
                    case_id=case.case_id,
                    backlog_amount_paise=case.backlog_amount_paise,
                    invoice_count=case.invoice_count,
                    halt_duration_days=case.halt_duration_days,
                    days_since_reactivation=_days_since(
                        case.reactivated_at, DECISION_NOW
                    ),
                    card_type=subscription.card_type.value,
                    risk_flags=tuple(customer.risk_flags),
                    historical_payment_success_rate=customer.historical_payment_success_rate,
                    previous_failure_count=customer.previous_failure_count,
                    previous_halt_count=customer.previous_halt_count,
                    subscription_age_days=customer.subscription_age_days,
                    allowed_actions=tuple(decision.allowed_actions),
                    requires_escalation=decision.requires_escalation,
                    stop=decision.stop,
                )
            )
            oracle_cases.append(
                OracleCase(
                    case_id=case.case_id,
                    customer_id=case.customer_id,
                    backlog_amount_paise=case.backlog_amount_paise,
                    historical_payment_success_rate=customer.historical_payment_success_rate,
                    has_dispute=customer.has_active_dispute,
                    customer_opted_out=customer.customer_opted_out,
                )
            )
        return views, oracle_cases, policies


# Names referenced by docs / tests so import-graph checks can see the split.
BASELINE_TYPES = (NaiveStrategy, RuleBasedStrategy)
