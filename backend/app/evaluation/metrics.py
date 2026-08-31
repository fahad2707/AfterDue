"""Benchmark metrics. Integer paise. Hidden outcomes used only here."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import asdict, dataclass

from app.domain.enums import ActionType
from app.evaluation.cases import EvalCase, unconstrained_preference
from app.simulator.costs import consumes_budget, cost_of
from app.simulator.oracle import OutcomeOracle
from app.simulator.strategies import CaseAction, CaseView


@dataclass(frozen=True)
class CaseContribution:
    case_id: str
    families: tuple[str, ...]
    collectible_recovered_paise: int
    no_action_recovered_paise: int
    incremental_paise: int
    cost_paise: int
    net_paise: int
    historical_targeted_paise: int
    invalid_targeted_paise: int
    collectible_targeted_paise: int
    intervened: bool
    unnecessary: bool
    policy_violation_attempted: bool
    policy_violation_executed: bool
    escalated: bool
    missed_collectible_paise: int


@dataclass(frozen=True)
class StrategyBenchmark:
    strategy_name: str
    universe: str
    eligible_cases: int
    historical_unpaid_paise: int
    truly_collectible_paise: int
    incorrectly_targeted_paise: int
    gross_recovered_paise: int
    collectible_recovered_paise: int
    recovery_rate_on_collectible: float
    intervention_cost_paise: int
    net_recovered_paise: int
    incremental_recovered_paise: int
    interventions: int
    unnecessary_interventions: int
    policy_violations_attempted: int
    policy_violations_executed: int
    human_escalations: int
    false_collectibility_rate: float
    missed_collectible_paise: int
    recovery_per_intervention_paise: int
    net_value_per_1000_cases_paise: int
    regret_vs_oracle_paise: int | None
    synthetic: bool = True


def score_strategy(
    *,
    name: str,
    universe: str,
    cases: list[EvalCase],
    views: list[CaseView],
    actions: list[CaseAction],
    oracle: OutcomeOracle,
    n_population_cases: int,
    collectible_universe_paise: int,
    historical_universe_paise: int,
) -> tuple[StrategyBenchmark, list[CaseContribution]]:
    by_action = {a.case_id: a.action for a in actions}
    by_case = {c.case_id: c for c in cases}
    if set(by_action) != {v.case_id for v in views}:
        raise RuntimeError(f"{name} did not decide on its assigned universe")

    contribs: list[CaseContribution] = []
    for view in views:
        case = by_case[view.case_id]
        action = by_action[view.case_id]
        selected = oracle.decide(case.oracle_case, action)
        counter = oracle.decide(case.oracle_case, ActionType.NO_ACTION)
        recovered = selected.amount_recovered_paise
        no_action = counter.amount_recovered_paise
        intervened = consumes_budget(action)
        preferred = unconstrained_preference(view)
        attempted = preferred not in view.allowed_actions and consumes_budget(preferred)
        executed = action not in view.allowed_actions
        invalid = case.invalid_amount_paise if intervened else 0
        historical_targeted = (
            view.backlog_amount_paise if intervened else 0
        )
        # Gated views only carry collectible rupees; ungated carry historical.
        if universe == "ungated" and intervened:
            collectible_targeted = case.collectible_amount_paise
            invalid = case.invalid_amount_paise
            historical_targeted = case.historical_unpaid_amount_paise
        elif intervened:
            collectible_targeted = view.backlog_amount_paise
            invalid = 0
            historical_targeted = view.backlog_amount_paise
        else:
            collectible_targeted = 0
        missed = 0
        if (
            case.collectible_amount_paise > 0
            and not intervened
            and any(consumes_budget(a) for a in view.allowed_actions)
        ):
            missed = case.collectible_amount_paise
        contribs.append(
            CaseContribution(
                case_id=case.case_id,
                families=case.families,
                collectible_recovered_paise=recovered,
                no_action_recovered_paise=no_action,
                incremental_paise=recovered - no_action,
                cost_paise=cost_of(action),
                net_paise=recovered - cost_of(action),
                historical_targeted_paise=historical_targeted,
                invalid_targeted_paise=invalid,
                collectible_targeted_paise=collectible_targeted,
                intervened=intervened,
                unnecessary=intervened and no_action > 0,
                policy_violation_attempted=attempted,
                policy_violation_executed=executed,
                escalated=action is ActionType.ESCALATE_TO_MERCHANT,
                missed_collectible_paise=missed,
            )
        )

    recovered = sum(c.collectible_recovered_paise for c in contribs)
    invalid = sum(c.invalid_targeted_paise for c in contribs)
    targeted_hist = sum(c.historical_targeted_paise for c in contribs)
    cost = sum(c.cost_paise for c in contribs)
    used = sum(1 for c in contribs if c.intervened)
    incremental = sum(c.incremental_paise for c in contribs)
    denom = collectible_universe_paise
    n = n_population_cases or 1
    return (
        StrategyBenchmark(
            strategy_name=name,
            universe=universe,
            eligible_cases=len(views),
            historical_unpaid_paise=historical_universe_paise,
            truly_collectible_paise=collectible_universe_paise,
            incorrectly_targeted_paise=invalid,
            gross_recovered_paise=recovered,
            collectible_recovered_paise=recovered,
            recovery_rate_on_collectible=(recovered / denom) if denom else 0.0,
            intervention_cost_paise=cost,
            net_recovered_paise=recovered - cost,
            incremental_recovered_paise=incremental,
            interventions=used,
            unnecessary_interventions=sum(1 for c in contribs if c.unnecessary),
            policy_violations_attempted=sum(
                1 for c in contribs if c.policy_violation_attempted
            ),
            policy_violations_executed=sum(
                1 for c in contribs if c.policy_violation_executed
            ),
            human_escalations=sum(1 for c in contribs if c.escalated),
            false_collectibility_rate=(invalid / targeted_hist) if targeted_hist else 0.0,
            missed_collectible_paise=sum(c.missed_collectible_paise for c in contribs),
            recovery_per_intervention_paise=(recovered // used) if used else 0,
            net_value_per_1000_cases_paise=((recovered - cost) * 1000) // n,
            regret_vs_oracle_paise=None,
        ),
        contribs,
    )


def with_regret(row: StrategyBenchmark, oracle_incremental: int) -> StrategyBenchmark:
    data = asdict(row)
    data["regret_vs_oracle_paise"] = oracle_incremental - row.incremental_recovered_paise
    return StrategyBenchmark(**data)


def family_breakdown(
    contribs: list[CaseContribution],
) -> dict[str, dict[str, int]]:
    grouped: dict[str, dict[str, int]] = defaultdict(
        lambda: {
            "cases": 0,
            "interventions": 0,
            "collectible_recovered_paise": 0,
            "incremental_paise": 0,
            "invalid_targeted_paise": 0,
        }
    )
    seen: dict[str, set[str]] = defaultdict(set)
    for row in contribs:
        for family in row.families:
            bucket = grouped[family]
            if row.case_id not in seen[family]:
                bucket["cases"] += 1
                seen[family].add(row.case_id)
            if row.intervened:
                bucket["interventions"] += 1
            bucket["collectible_recovered_paise"] += row.collectible_recovered_paise
            bucket["incremental_paise"] += row.incremental_paise
            bucket["invalid_targeted_paise"] += row.invalid_targeted_paise
    return dict(grouped)
