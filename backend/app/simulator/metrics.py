from dataclasses import dataclass

from app.domain.enums import ActionType
from app.simulator.costs import consumes_budget, cost_of
from app.simulator.oracle import OracleOutcome
from app.simulator.strategies import CaseAction, CaseView


@dataclass(frozen=True)
class StrategyMetrics:
    strategy_name: str
    eligible_cases: int
    intervention_budget: int
    interventions_used: int
    revenue_at_risk_paise: int
    revenue_recovered_paise: int
    recovery_yield: float
    recovered_case_count: int
    failed_intervention_count: int
    escalation_count: int
    no_action_count: int
    revenue_per_intervention_paise: int
    revenue_per_100_cases_paise: int
    unnecessary_intervention_count: int
    incremental_revenue_paise: int
    action_cost_paise: int
    synthetic: bool = True


def aggregate_metrics(
    *,
    strategy_name: str,
    budget: int,
    views: list[CaseView],
    actions: list[CaseAction],
    selected: dict[str, OracleOutcome],
    no_action: dict[str, OracleOutcome],
) -> StrategyMetrics:
    by_id = {a.case_id: a.action for a in actions}
    at_risk = sum(v.backlog_amount_paise for v in views)
    recovered = 0
    recovered_cases = 0
    failed = 0
    escalations = 0
    no_actions = 0
    used = 0
    unnecessary = 0
    incremental = 0
    costs = 0

    for view in views:
        action = by_id[view.case_id]
        outcome = selected[view.case_id]
        counter = no_action[view.case_id]
        costs += cost_of(action)
        if consumes_budget(action):
            used += 1
            if counter.amount_recovered_paise > 0:
                unnecessary += 1
        if action is ActionType.NO_ACTION:
            no_actions += 1
        if action is ActionType.ESCALATE_TO_MERCHANT:
            escalations += 1
        recovered += outcome.amount_recovered_paise
        incremental += outcome.amount_recovered_paise - counter.amount_recovered_paise
        if outcome.outcome == "paid":
            recovered_cases += 1
        elif consumes_budget(action) and outcome.outcome == "failed":
            failed += 1

    n = len(views)
    yield_ = (recovered / at_risk) if at_risk else 0.0
    per_int = (recovered // used) if used else 0
    per_100 = (recovered * 100 // n) if n else 0

    return StrategyMetrics(
        strategy_name=strategy_name,
        eligible_cases=n,
        intervention_budget=budget,
        interventions_used=used,
        revenue_at_risk_paise=at_risk,
        revenue_recovered_paise=recovered,
        recovery_yield=round(yield_, 6),
        recovered_case_count=recovered_cases,
        failed_intervention_count=failed,
        escalation_count=escalations,
        no_action_count=no_actions,
        revenue_per_intervention_paise=per_int,
        revenue_per_100_cases_paise=per_100,
        unnecessary_intervention_count=unnecessary,
        incremental_revenue_paise=incremental,
        action_cost_paise=costs,
    )
