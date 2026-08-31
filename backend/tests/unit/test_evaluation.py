"""Collectibility-aware evaluation layer. No Mongo."""

import inspect

from app.domain.enums import ActionType
from app.evaluation.benchmark import run_benchmark
from app.evaluation.cases import build_eval_cases
from app.evaluation.config import EvaluationConfig
from app.evaluation.metrics import score_strategy
from app.simulator.oracle import OutcomeOracle
from app.simulator.strategies import NaiveStrategy


def _cfg(**kw) -> EvaluationConfig:
    body = dict(subscriber_count=80, seed=42, bootstrap_samples=50, include_oracle=True)
    body.update(kw)
    return EvaluationConfig(**body)


def test_same_seed_same_eval_cases():
    sim = _cfg().simulation()
    assert build_eval_cases(sim) == build_eval_cases(sim)


def test_collectible_buckets_sum_to_historical():
    cases = build_eval_cases(_cfg(seed=7).simulation())
    assert cases
    for case in cases:
        total = (
            case.collectible_amount_paise
            + case.not_collectible_amount_paise
            + case.review_required_amount_paise
        )
        assert total == case.historical_unpaid_amount_paise
        assert type(case.historical_unpaid_amount_paise) is int
        assert type(case.collectible_amount_paise) is int


def test_naive_universe_includes_non_collectible_cases():
    cases = build_eval_cases(_cfg(seed=11).simulation())
    gated = [c for c in cases if c.gated_view is not None]
    assert len(cases) >= len(gated)
    zero = [c for c in cases if c.collectible_amount_paise == 0]
    assert zero
    assert all(
        c.ungated_view.backlog_amount_paise == c.historical_unpaid_amount_paise
        for c in zero
    )
    assert all(c.gated_view is None for c in zero)


def test_gated_views_are_collectible_only():
    cases = build_eval_cases(_cfg().simulation())
    for case in cases:
        if case.gated_view is None:
            continue
        assert case.gated_view.backlog_amount_paise == case.collectible_amount_paise
        assert case.gated_view.invoice_count == case.collectible_invoice_count
        assert case.collectible_amount_paise > 0


def test_baselines_are_independent_modules():
    import app.simulator.strategies as strategies_mod

    source = inspect.getsource(strategies_mod)
    assert "app.evaluation" not in source
    assert "from app.simulator.oracle" not in source
    assert "OracleStrategy" not in source
    assert not hasattr(strategies_mod, "latent_payment_intent")


def test_no_hidden_outcome_leakage_into_views():
    cases = build_eval_cases(_cfg().simulation())
    params = list(inspect.signature(cases[0].ungated_view.__class__).parameters)
    assert "latent_payment_intent" not in params
    view = cases[0].ungated_view
    assert not hasattr(view, "latent_payment_intent")
    naive = NaiveStrategy().choose_actions([c.ungated_view for c in cases], 5)
    assert all(a.action in ActionType for a in naive)


def test_oracle_recovery_never_exceeds_collectible():
    cases = build_eval_cases(_cfg(seed=3).simulation())
    oracle = OutcomeOracle(3)
    for case in cases:
        for action in ActionType:
            paid = oracle.decide(case.oracle_case, action).amount_recovered_paise
            assert paid in (0, case.collectible_amount_paise)
            assert paid <= case.collectible_amount_paise


def test_naive_can_target_invalid_debt():
    cases = build_eval_cases(_cfg(seed=11, subscriber_count=120).simulation())
    views = [c.ungated_view for c in cases]
    actions = NaiveStrategy().choose_actions(views, 40)
    oracle = OutcomeOracle(11)
    row, _ = score_strategy(
        name="naive",
        universe="ungated",
        cases=cases,
        views=views,
        actions=actions,
        oracle=oracle,
        n_population_cases=len(cases),
        collectible_universe_paise=sum(c.collectible_amount_paise for c in cases),
        historical_universe_paise=sum(c.historical_unpaid_amount_paise for c in cases),
    )
    assert row.incorrectly_targeted_paise > 0
    assert row.policy_violations_executed == 0
    assert type(row.net_recovered_paise) is int


def test_rule_based_and_reclaim_share_gated_universe():
    report = run_benchmark(_cfg(subscriber_count=80, seed=42, bootstrap_samples=50))
    rule = report.strategies["rule_based"]
    reclaim = report.strategies["reclaim"]
    assert rule.universe == reclaim.universe == "gated"
    assert rule.eligible_cases == reclaim.eligible_cases
    assert rule.eligible_cases == report.population.gated_case_count
    assert report.strategies["naive"].universe == "ungated"
    assert report.strategies["naive"].eligible_cases == report.population.case_count


def test_reproducible_benchmark():
    a = run_benchmark(_cfg(seed=42, bootstrap_samples=50))
    b = run_benchmark(_cfg(seed=42, bootstrap_samples=50))
    assert a.population == b.population
    assert a.strategies["naive"] == b.strategies["naive"]
    assert a.strategies["rule_based"] == b.strategies["rule_based"]
    assert a.strategies["reclaim"] == b.strategies["reclaim"]
    assert a.strategies["oracle"] == b.strategies["oracle"]


def test_policy_violations_are_not_executed():
    report = run_benchmark(_cfg(seed=5, bootstrap_samples=50))
    for row in report.strategies.values():
        assert row.policy_violations_executed == 0


def test_partial_collectible_family_exists_without_hardcoding_amounts():
    cases = build_eval_cases(_cfg(subscriber_count=150, seed=42).simulation())
    mixed = [c for c in cases if "partially_collectible" in c.families]
    assert mixed
    sample = mixed[0]
    assert sample.historical_unpaid_amount_paise > sample.collectible_amount_paise
    assert sample.collectible_amount_paise > 0
    assert sample.invalid_amount_paise > 0


def test_oracle_regret_is_reported_without_claiming_a_realized_bound():
    report = run_benchmark(_cfg(seed=42, bootstrap_samples=50))
    assert "oracle" in report.strategies
    for name in ("naive", "rule_based", "reclaim"):
        regret = report.strategies[name].regret_vs_oracle_paise
        assert regret is not None
        assert type(regret) is int
    # Expected-value oracle is not clairvoyant; a strategy may get lucky.


def test_different_seed_changes_world():
    a = run_benchmark(_cfg(seed=42, bootstrap_samples=50))
    b = run_benchmark(_cfg(seed=43, bootstrap_samples=50))
    assert a.population.historical_unpaid_paise != b.population.historical_unpaid_paise or (
        a.strategies["reclaim"].incremental_recovered_paise
        != b.strategies["reclaim"].incremental_recovered_paise
    )
