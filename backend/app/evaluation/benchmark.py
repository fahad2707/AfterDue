"""Run the collectibility-aware strategy benchmark.

Naive sees ungated historical unpaid. Rule-based, RECLAIM, and the oracle
reference policy see the production collectibility-gated universe.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass

from app.evaluation.bootstrap import interval_for
from app.evaluation.cases import EvalCase, build_eval_cases
from app.evaluation.config import EvaluationConfig
from app.evaluation.diagnostics import action_agreement, action_mix, diagnose_ties
from app.evaluation.metrics import (
    CaseContribution,
    StrategyBenchmark,
    family_breakdown,
    score_strategy,
    with_regret,
)
from app.evaluation.oracle_strategy import OracleStrategy
from app.evaluation.scenarios import FAMILY_LABELS
from app.ml.strategy import ReclaimStrategy
from app.simulator.oracle import OutcomeOracle
from app.simulator.strategies import CaseAction, CaseView, NaiveStrategy, RuleBasedStrategy


@dataclass(frozen=True)
class PopulationTotals:
    subscriber_count: int
    case_count: int
    gated_case_count: int
    review_only_case_count: int
    excluded_only_case_count: int
    historical_unpaid_paise: int
    collectible_paise: int
    not_collectible_paise: int
    review_required_paise: int
    human_review_rate: float
    intervention_budget: int
    seed: int
    synthetic: bool = True


@dataclass(frozen=True)
class BenchmarkReport:
    population: PopulationTotals
    strategies: dict[str, StrategyBenchmark]
    intervals: dict[str, dict[str, dict]]
    scenario_breakdown: dict[str, dict[str, dict[str, int]]]
    diagnostics: list[str]
    action_agreement: dict[str, float]
    action_mix: dict[str, dict[str, int]]
    family_labels: dict[str, str]
    synthetic: bool = True
    limitations: tuple[str, ...] = (
        "Evaluation uses synthetic lifecycle data, not merchant production data.",
        "Recovery outcomes are simulated by a seeded oracle.",
        "Results do not represent real Razorpay recovery rates.",
        "Model estimates are prototype estimates from the same synthetic family.",
        "Real-world validation would require merchant outcome data.",
    )


def _gated(cases: list[EvalCase]) -> list[EvalCase]:
    return [c for c in cases if c.gated_view is not None]


def _choose(
    name: str,
    views: list[CaseView],
    budget: int,
    seed: int,
) -> list[CaseAction]:
    if name == "naive":
        return NaiveStrategy().choose_actions(views, budget)
    if name == "rule_based":
        return RuleBasedStrategy().choose_actions(views, budget)
    if name == "reclaim":
        return ReclaimStrategy().choose_actions(views, budget)
    if name == "oracle":
        return OracleStrategy(seed).choose_actions(views, budget)
    raise ValueError(f"unknown evaluation strategy {name}")


def run_benchmark(config: EvaluationConfig) -> BenchmarkReport:
    sim = config.simulation()
    cases = build_eval_cases(sim)
    gated_cases = _gated(cases)
    ungated_views = [c.ungated_view for c in cases]
    gated_views = [c.gated_view for c in gated_cases if c.gated_view is not None]
    budget = sim.intervention_budget
    oracle = OutcomeOracle(sim.seed)
    historical = sum(c.historical_unpaid_amount_paise for c in cases)
    collectible = sum(c.collectible_amount_paise for c in cases)
    excluded = sum(c.not_collectible_amount_paise for c in cases)
    review = sum(c.review_required_amount_paise for c in cases)
    review_only = sum(
        1
        for c in cases
        if c.collectible_amount_paise == 0 and c.review_required_amount_paise > 0
    )
    excluded_only = sum(
        1
        for c in cases
        if c.collectible_amount_paise == 0
        and c.not_collectible_amount_paise > 0
        and c.review_required_amount_paise == 0
    )
    population = PopulationTotals(
        subscriber_count=sim.subscriber_count,
        case_count=len(cases),
        gated_case_count=len(gated_cases),
        review_only_case_count=review_only,
        excluded_only_case_count=excluded_only,
        historical_unpaid_paise=historical,
        collectible_paise=collectible,
        not_collectible_paise=excluded,
        review_required_paise=review,
        human_review_rate=(review / historical) if historical else 0.0,
        intervention_budget=budget,
        seed=sim.seed,
    )

    assignments: dict[str, tuple[str, list[CaseView]]] = {
        "naive": ("ungated", ungated_views),
        "rule_based": ("gated", gated_views),
        "reclaim": ("gated", gated_views),
    }
    if config.include_oracle:
        assignments["oracle"] = ("gated", gated_views)

    results: dict[str, StrategyBenchmark] = {}
    contrib_map: dict[str, list[CaseContribution]] = {}
    action_map: dict[str, list[CaseAction]] = {}
    for name, (universe, views) in assignments.items():
        chosen = _choose(name, views, budget, sim.seed)
        action_map[name] = chosen
        row, contribs = score_strategy(
            name=name,
            universe=universe,
            cases=cases,
            views=views,
            actions=chosen,
            oracle=oracle,
            n_population_cases=len(cases),
            collectible_universe_paise=collectible,
            historical_universe_paise=historical,
        )
        results[name] = row
        contrib_map[name] = contribs

    if "oracle" in results:
        oracle_inc = results["oracle"].incremental_recovered_paise
        results = {
            name: with_regret(row, oracle_inc) if name != "oracle" else row
            for name, row in results.items()
        }

    intervals = {}
    for name, contribs in contrib_map.items():
        intervals[name] = {
            "net_recovered_paise": interval_for(
                contribs,
                field="net_paise",
                samples=config.bootstrap_samples,
                seed=sim.seed + 17,
            ).__dict__,
            "incremental_recovered_paise": interval_for(
                contribs,
                field="incremental_paise",
                samples=config.bootstrap_samples,
                seed=sim.seed + 23,
            ).__dict__,
            "collectible_recovered_paise": interval_for(
                contribs,
                field="collectible_recovered_paise",
                samples=config.bootstrap_samples,
                seed=sim.seed + 29,
            ).__dict__,
        }

    breakdown = {
        name: family_breakdown(contribs) for name, contribs in contrib_map.items()
    }
    agreement = {}
    if "reclaim" in action_map and "rule_based" in action_map:
        agreement["reclaim_vs_rule_based"] = action_agreement(
            action_map["reclaim"], action_map["rule_based"]
        )
    if "reclaim" in action_map and "naive" in action_map:
        agreement["reclaim_vs_naive"] = action_agreement(
            action_map["reclaim"], action_map["naive"]
        )
    if "oracle" in action_map and "reclaim" in action_map:
        agreement["reclaim_vs_oracle"] = action_agreement(
            action_map["reclaim"], action_map["oracle"]
        )

    diagnostics = diagnose_ties(
        results=results,
        actions=action_map,
        gated_views=gated_views,
        budget=budget,
    )
    return BenchmarkReport(
        population=population,
        strategies=results,
        intervals=intervals,
        scenario_breakdown=breakdown,
        diagnostics=diagnostics,
        action_agreement=agreement,
        action_mix={name: action_mix(rows) for name, rows in action_map.items()},
        family_labels=dict(FAMILY_LABELS),
    )


def report_to_dict(report: BenchmarkReport) -> dict:
    payload = asdict(report)
    payload["strategies"] = {
        name: asdict(row) for name, row in report.strategies.items()
    }
    payload["population"] = asdict(report.population)
    payload["limitations"] = list(report.limitations)
    payload["synthetic"] = True
    return payload
