import inspect

from app.domain.enums import ActionType
from app.simulator.config import SimulationConfig
from app.simulator.costs import consumes_budget
from app.simulator.metrics import aggregate_metrics
from app.simulator.oracle import (
    OracleCase,
    OutcomeOracle,
    latent_payment_intent,
    recovery_probability,
)
from app.simulator.population import Fate, draw_population
from app.simulator.strategies import (
    CaseAction,
    CaseView,
    NaiveStrategy,
    RuleBasedStrategy,
    rule_based_score,
)


def _view(case_id: str, backlog: int = 499900, **kw) -> CaseView:
    defaults = dict(
        case_id=case_id,
        backlog_amount_paise=backlog,
        invoice_count=2,
        halt_duration_days=60,
        days_since_reactivation=20,
        card_type="international",
        risk_flags=(),
        historical_payment_success_rate=0.8,
        previous_failure_count=1,
        previous_halt_count=1,
        subscription_age_days=400,
        allowed_actions=(
            ActionType.NO_ACTION,
            ActionType.SEND_PAYMENT_LINK,
            ActionType.ATTEMPT_MANUAL_CHARGE,
            ActionType.ESCALATE_TO_MERCHANT,
        ),
        requires_escalation=False,
        stop=False,
    )
    defaults.update(kw)
    return CaseView(**defaults)


def test_same_seed_same_population():
    cfg = SimulationConfig(subscriber_count=40, seed=42)
    assert draw_population(cfg) == draw_population(cfg)


def test_different_seed_different_population():
    a = draw_population(SimulationConfig(subscriber_count=40, seed=42))
    b = draw_population(SimulationConfig(subscriber_count=40, seed=43))
    assert [p.plan_amount_paise for p in a] != [p.plan_amount_paise for p in b] or [
        p.fate for p in a
    ] != [p.fate for p in b]


def test_population_money_is_integer_paise():
    for person in draw_population(SimulationConfig(subscriber_count=30, seed=7)):
        assert isinstance(person.plan_amount_paise, int)
        assert person.plan_amount_paise >= 49900


def test_only_reactivated_plans_are_recovery_candidates():
    people = draw_population(SimulationConfig(subscriber_count=80, seed=42))
    assert any(p.fate is Fate.ALWAYS_ACTIVE for p in people)
    assert any(p.fate is Fate.HALTED_NEVER_RETURNED for p in people)
    assert any(p.fate is Fate.REACTIVATED for p in people)
    assert any(p.halt_cycles == 2 for p in people if p.fate is Fate.REACTIVATED)


def test_oracle_is_deterministic():
    case = OracleCase("case_x", "cust_x", 1499700, 0.7, False, False)
    oracle = OutcomeOracle(42)
    first = oracle.decide(case, ActionType.SEND_PAYMENT_LINK)
    second = oracle.decide(case, ActionType.SEND_PAYMENT_LINK)
    assert first == second


def test_oracle_supports_no_action_and_action_specific_outcomes():
    case = OracleCase("case_y", "cust_y", 499900, 0.6, False, False)
    oracle = OutcomeOracle(42)
    none = oracle.decide(case, ActionType.NO_ACTION)
    link = oracle.decide(case, ActionType.SEND_PAYMENT_LINK)
    charge = oracle.decide(case, ActionType.ATTEMPT_MANUAL_CHARGE)
    assert none.synthetic is True
    assert {none.outcome, link.outcome, charge.outcome} <= {
        "paid",
        "failed",
        "pending",
        "escalated",
    }
    # Different actions may differ; the contract is they are independently callable.
    assert isinstance(none.amount_recovered_paise, int)


def test_oracle_uses_hidden_latent_variable():
    low = recovery_probability(
        ActionType.NO_ACTION,
        latent=0.05,
        historical_success=0.5,
        has_dispute=False,
        opted_out=False,
    )
    high = recovery_probability(
        ActionType.NO_ACTION,
        latent=0.95,
        historical_success=0.5,
        has_dispute=False,
        opted_out=False,
    )
    assert high > low
    assert 0.0 <= latent_payment_intent(42, "cust_a") <= 1.0
    assert latent_payment_intent(42, "cust_a") == latent_payment_intent(42, "cust_a")
    assert latent_payment_intent(42, "cust_a") != latent_payment_intent(42, "cust_b")


def test_strategy_module_cannot_see_oracle_or_latent():
    import app.simulator.strategies as strategies_mod

    assert not hasattr(strategies_mod, "OutcomeOracle")
    assert not hasattr(strategies_mod, "latent_payment_intent")
    imported = inspect.getsource(strategies_mod)
    assert "from app.simulator.oracle" not in imported
    assert "import app.simulator.oracle" not in imported
    sig = inspect.signature(NaiveStrategy.choose_actions)
    assert "latent" not in sig.parameters
    params = list(inspect.signature(CaseView).parameters)
    assert "latent_payment_intent" not in params


def test_naive_and_rule_based_are_deterministic_and_respect_budget():
    views = [_view(f"case_{i:03d}", backlog=100000 * (i + 1)) for i in range(12)]
    budget = 4
    naive_a = NaiveStrategy().choose_actions(views, budget)
    naive_b = NaiveStrategy().choose_actions(views, budget)
    rule_a = RuleBasedStrategy().choose_actions(views, budget)
    rule_b = RuleBasedStrategy().choose_actions(views, budget)
    assert naive_a == naive_b
    assert rule_a == rule_b
    assert sum(1 for a in naive_a if consumes_budget(a.action)) <= budget
    assert sum(1 for a in rule_a if consumes_budget(a.action)) <= budget
    assert sum(1 for a in naive_a if a.action is ActionType.NO_ACTION) >= 8


def test_no_action_does_not_consume_budget():
    views = [
        _view(
            "case_esc",
            allowed_actions=(ActionType.NO_ACTION, ActionType.ESCALATE_TO_MERCHANT),
            requires_escalation=True,
            stop=True,
        )
    ]
    actions = NaiveStrategy().choose_actions(views, intervention_budget=0)
    assert actions[0].action is ActionType.ESCALATE_TO_MERCHANT
    assert not consumes_budget(actions[0].action)


def test_strategies_obey_policy_allowed_actions():
    views = [
        _view(
            "case_dom",
            allowed_actions=(ActionType.NO_ACTION, ActionType.SEND_PAYMENT_LINK),
        ),
        _view(
            "case_risk",
            allowed_actions=(ActionType.NO_ACTION, ActionType.ESCALATE_TO_MERCHANT),
            requires_escalation=True,
            risk_flags=("chargeback",),
        ),
    ]
    for strategy in (NaiveStrategy(), RuleBasedStrategy()):
        for choice in strategy.choose_actions(views, 10):
            allowed = next(v.allowed_actions for v in views if v.case_id == choice.case_id)
            assert choice.action in allowed
            if choice.case_id == "case_dom":
                assert choice.action is not ActionType.ATTEMPT_MANUAL_CHARGE


def test_rule_based_does_not_use_oracle_and_ranks_by_documented_score():
    cheap = _view("case_small", backlog=49900, historical_payment_success_rate=0.1)
    rich = _view("case_big", backlog=1999900, historical_payment_success_rate=0.9)
    assert rule_based_score(rich) > rule_based_score(cheap)
    actions = RuleBasedStrategy().choose_actions([cheap, rich], 1)
    assert actions[0].case_id == "case_big"
    assert actions[0].action is ActionType.SEND_PAYMENT_LINK


def test_metrics_incremental_and_unnecessary_from_no_action_counterfactual():
    views = [_view("a", 1000), _view("b", 2000)]
    actions = [
        CaseAction("a", ActionType.SEND_PAYMENT_LINK),
        CaseAction("b", ActionType.NO_ACTION),
    ]
    from app.simulator.oracle import OracleOutcome

    selected = {
        "a": OracleOutcome("paid", 1000),
        "b": OracleOutcome("failed", 0),
    }
    no_action = {
        "a": OracleOutcome("paid", 1000),  # would have paid anyway
        "b": OracleOutcome("failed", 0),
    }
    metrics = aggregate_metrics(
        strategy_name="naive",
        budget=5,
        views=views,
        actions=actions,
        selected=selected,
        no_action=no_action,
    )
    assert metrics.revenue_at_risk_paise == 3000
    assert metrics.revenue_recovered_paise == 1000
    assert metrics.recovery_yield == round(1000 / 3000, 6)
    assert metrics.unnecessary_intervention_count == 1
    assert metrics.incremental_revenue_paise == 0
    assert metrics.interventions_used == 1
    assert metrics.revenue_per_intervention_paise == 1000
    assert isinstance(metrics.revenue_recovered_paise, int)
    assert metrics.synthetic is True
