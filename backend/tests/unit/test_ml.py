"""M5: shared features, anti-leakage, economics, training, RECLAIM strategy."""

from __future__ import annotations

import inspect
from pathlib import Path

import joblib
import numpy as np
import pytest
from sklearn.linear_model import LogisticRegression

from app.domain.enums import ActionType
from app.ml.dataset import generate_training_rows
from app.ml.economics import incremental_ev_paise, uplift
from app.ml.errors import FeatureSchemaMismatch
from app.ml.features import (
    FEATURE_NAMES,
    FORBIDDEN_FEATURE_TOKENS,
    build_features,
    feature_schema_hash,
    rows_to_frame,
)
from app.ml.predict import predict_probability
from app.ml.registry import load_artifact, save_artifact
from app.ml.strategy import ReclaimStrategy
from app.ml.train import group_split, make_pipeline, train_and_select
from app.simulator.config import SimulationConfig
from app.simulator.costs import cost_of
from app.simulator.population import collectible_cycle_count, draw_population
from app.simulator.strategies import CaseAction, NaiveStrategy, RuleBasedStrategy
from tests.unit.test_simulator import _view


def test_train_and_inference_use_same_feature_builder():
    assert build_features.__module__ == "app.ml.features"
    view = _view("c1")
    train_row = build_features(view, ActionType.SEND_PAYMENT_LINK)
    serve_row = build_features(view, ActionType.SEND_PAYMENT_LINK)
    assert train_row.values == serve_row.values
    assert train_row.schema_hash == serve_row.schema_hash == feature_schema_hash()


def test_hidden_latent_and_oracle_tokens_absent_from_features():
    values = build_features(_view("c1"), ActionType.NO_ACTION).values
    lowered = {name.lower() for name in values}
    assert not FORBIDDEN_FEATURE_TOKENS.intersection(lowered)
    assert "latent_payment_intent" not in inspect.signature(_view("c1").__class__).parameters


def test_feature_schema_stable_and_hash_changes_when_schema_changes():
    first = feature_schema_hash()
    second = feature_schema_hash()
    assert first == second
    assert first == feature_schema_hash(FEATURE_NAMES)
    mutated = FEATURE_NAMES + ("extra_secret",)
    assert feature_schema_hash(mutated) != first


def test_model_rejects_incompatible_schema(tmp_path: Path):
    view = _view("c1")
    row = build_features(view, ActionType.NO_ACTION)
    frame = rows_to_frame([row, build_features(_view("c2"), ActionType.SEND_PAYMENT_LINK)])
    y = np.array([0, 1])
    pipe = make_pipeline(LogisticRegression(max_iter=200))
    pipe.fit(frame, y)
    dest = tmp_path / "bad.joblib"
    save_artifact(
        pipe,
        {
            "feature_schema_hash": "not-the-current-hash",
            "feature_names": list(FEATURE_NAMES),
        },
        dest,
    )
    with pytest.raises(FeatureSchemaMismatch):
        load_artifact(dest)


def test_money_stays_integer_paise():
    ev = incremental_ev_paise(1_000_000, ActionType.SEND_PAYMENT_LINK, 0.67, 0.31)
    assert isinstance(ev, int)
    assert ev == int(round(1_000_000 * 0.36 - cost_of(ActionType.SEND_PAYMENT_LINK)))


def test_training_reproducible_for_same_dataset_seed():
    a = generate_training_rows(7, 80)
    b = generate_training_rows(7, 80)
    assert [(r.group_id, r.action, r.recovered) for r in a] == [
        (r.group_id, r.action, r.recovered) for r in b
    ]


def test_group_split_prevents_case_leakage():
    rows = generate_training_rows(3, 240)
    groups = [row.group_id for row in rows]
    split = group_split(groups, 3)
    train = {groups[i] for i in split.train_idx}
    val = {groups[i] for i in split.val_idx}
    test = {groups[i] for i in split.test_idx}
    assert not (train & val)
    assert not (train & test)
    assert not (val & test)
    assert len(split.test_idx) > 0


def test_action_assignment_randomized_and_includes_no_action():
    rows = generate_training_rows(11, 400)
    actions = {row.action for row in rows}
    assert ActionType.NO_ACTION in actions
    assert ActionType.SEND_PAYMENT_LINK in actions
    assert ActionType.ATTEMPT_MANUAL_CHARGE in actions
    # Domestic-card policy makes manual charge rare; it must still appear.
    by_action = {a: 0 for a in actions}
    for row in rows:
        by_action[row.action] += 1
    assert by_action[ActionType.NO_ACTION] > 50
    assert by_action[ActionType.SEND_PAYMENT_LINK] > 50
    assert by_action[ActionType.ATTEMPT_MANUAL_CHARGE] >= 1


def test_pipeline_roundtrip_predictions_match(tmp_path: Path):
    result = train_and_select(dataset_seed=5, n_examples=360)
    view = result and generate_training_rows(5, 20)[0].view
    before = [
        predict_probability(result["pipeline"], view, action)
        for action in (ActionType.NO_ACTION, ActionType.SEND_PAYMENT_LINK)
    ]
    dest = tmp_path / "model.joblib"
    save_artifact(result["pipeline"], result["metadata"], dest)
    loaded, meta = load_artifact(dest)
    after = [
        predict_probability(loaded, view, action)
        for action in (ActionType.NO_ACTION, ActionType.SEND_PAYMENT_LINK)
    ]
    assert before == pytest.approx(after)
    assert meta["feature_schema_hash"] == feature_schema_hash()
    again = joblib.load(dest)
    assert "pipeline" in again


def test_uplift_and_incremental_ev_formulas():
    assert uplift(0.67, 0.31) == pytest.approx(0.36)
    ev = incremental_ev_paise(1_000_000, ActionType.SEND_PAYMENT_LINK, 0.67, 0.31)
    assert ev == 1_000_000 * 36 // 100 - 200
    assert incremental_ev_paise(1_000_000, ActionType.NO_ACTION, 0.31, 0.31) == 0
    charged = incremental_ev_paise(1_000_000, ActionType.ATTEMPT_MANUAL_CHARGE, 0.54, 0.31)
    assert charged == int(round(1_000_000 * 0.23 - 500))


class _FixedPipe:
    def __init__(self, probs: dict[ActionType, float]):
        self.probs = probs

    def predict_proba(self, frame):
        action = ActionType(frame.iloc[0]["action"])
        p = self.probs[action]
        return np.array([[1 - p, p]])


def _strategy_from_probs(probs: dict[ActionType, float]) -> ReclaimStrategy:
    return ReclaimStrategy(
        pipeline=_FixedPipe(probs),  # type: ignore[arg-type]
        metadata={"model_version": "test", "model_type": "stub"},
    )


def test_negative_ev_chooses_no_action():
    view = _view("neg", backlog=10_000)
    strategy = _strategy_from_probs(
        {
            ActionType.NO_ACTION: 0.40,
            ActionType.SEND_PAYMENT_LINK: 0.40,
            ActionType.ATTEMPT_MANUAL_CHARGE: 0.41,
        }
    )
    chosen = strategy.choose_actions([view], 10)
    assert chosen[0].action is ActionType.NO_ACTION


def test_blocked_action_never_selected():
    view = _view(
        "blocked",
        backlog=2_000_000,
        allowed_actions=(ActionType.NO_ACTION, ActionType.SEND_PAYMENT_LINK),
    )
    strategy = _strategy_from_probs(
        {
            ActionType.NO_ACTION: 0.10,
            ActionType.SEND_PAYMENT_LINK: 0.20,
            ActionType.ATTEMPT_MANUAL_CHARGE: 0.99,
        }
    )
    analysis = strategy.analyze(view)
    assert all(s.action is not ActionType.ATTEMPT_MANUAL_CHARGE for s in analysis.scores)
    assert strategy.choose_actions([view], 10)[0].action is not ActionType.ATTEMPT_MANUAL_CHARGE


def test_highest_positive_allowed_ev_selected():
    view = _view("best", backlog=1_000_000)
    strategy = _strategy_from_probs(
        {
            ActionType.NO_ACTION: 0.20,
            ActionType.SEND_PAYMENT_LINK: 0.80,
            ActionType.ATTEMPT_MANUAL_CHARGE: 0.50,
        }
    )
    assert strategy.choose_actions([view], 1)[0].action is ActionType.SEND_PAYMENT_LINK


def test_global_budget_respected():
    views = [_view(f"c{i}", backlog=1_000_000 + i) for i in range(6)]
    strategy = _strategy_from_probs(
        {
            ActionType.NO_ACTION: 0.10,
            ActionType.SEND_PAYMENT_LINK: 0.70,
            ActionType.ATTEMPT_MANUAL_CHARGE: 0.40,
        }
    )
    chosen = strategy.choose_actions(views, 2)
    used = sum(1 for a in chosen if a.action is not ActionType.NO_ACTION)
    assert used == 2
    assert all(a.action in a_view.allowed_actions for a, a_view in zip(chosen, views, strict=True))


def test_reclaim_strategy_does_not_import_oracle_or_latent():
    import app.ml.strategy as strategy_mod

    source = inspect.getsource(strategy_mod)
    assert "from app.simulator.oracle" not in source
    assert "import app.simulator.oracle" not in source
    assert "latent_payment_intent" not in source
    params = inspect.signature(ReclaimStrategy.choose_actions).parameters
    assert "latent_payment_intent" not in params


def test_reclaim_deterministic_and_same_budget_as_baselines():
    views = [_view(f"case_{i:03d}", backlog=80_000 * (i + 1)) for i in range(10)]
    result = train_and_select(dataset_seed=9, n_examples=360)
    reclaim = ReclaimStrategy(result["pipeline"], result["metadata"])
    first = reclaim.choose_actions(views, 3)
    second = reclaim.choose_actions(views, 3)
    assert first == second
    naive = NaiveStrategy().choose_actions(views, 3)
    rule = RuleBasedStrategy().choose_actions(views, 3)

    def used(actions: list[CaseAction]) -> int:
        return sum(
            1
            for a in actions
            if a.action in {ActionType.SEND_PAYMENT_LINK, ActionType.ATTEMPT_MANUAL_CHARGE}
        )

    assert used(first) <= 3
    assert used(naive) <= 3
    assert used(rule) <= 3


def test_escalations_preserved_and_no_unsupported_actions():
    views = [
        _view(
            "esc",
            allowed_actions=(ActionType.NO_ACTION, ActionType.ESCALATE_TO_MERCHANT),
            requires_escalation=True,
            stop=True,
        ),
        _view("ok", backlog=900_000),
    ]
    result = train_and_select(dataset_seed=2, n_examples=320)
    chosen = ReclaimStrategy(result["pipeline"], result["metadata"]).choose_actions(views, 1)
    by_id = {c.case_id: c.action for c in chosen}
    assert by_id["esc"] is ActionType.ESCALATE_TO_MERCHANT
    assert by_id["ok"] in views[1].allowed_actions


def test_classification_brier_calibration_and_held_out_only():
    result = train_and_select(dataset_seed=4, n_examples=420)
    test = result["test"]
    metadata = result["metadata"]
    assert test.precision >= 0
    assert test.recall >= 0
    assert 0 <= test.f1 <= 1
    assert 0 <= test.roc_auc <= 1
    assert 0 <= test.brier <= 1
    assert test.calibration_bins["mean_predicted"]
    assert test.calibration_bins["fraction_positive"]
    assert metadata["split"]["method"].startswith("GroupShuffleSplit")
    assert "validation" in metadata
    assert "test" in metadata
    assert metadata["selection_reason"]
    # Selection text refers to validation Brier, not the test split.
    assert "validation Brier" in metadata["selection_reason"]
    assert "test" not in metadata["selection_reason"]


def test_canonical_three_strategy_experiment_is_fair():
    result = train_and_select(dataset_seed=42, n_examples=480)
    views = [
        _view(
            f"sub_{i:04d}_halt_01",
            backlog=100_000 * ((i % 8) + 1),
            days_since_reactivation=10 + i,
        )
        for i in range(20)
    ]
    budget = 5
    reclaim = ReclaimStrategy(result["pipeline"], result["metadata"]).choose_actions(views, budget)
    naive = NaiveStrategy().choose_actions(views, budget)
    rule = RuleBasedStrategy().choose_actions(views, budget)
    assert {a.case_id for a in reclaim} == {v.case_id for v in views}
    for bundle in (reclaim, naive, rule):
        used = sum(
            1
            for a in bundle
            if a.action in {ActionType.SEND_PAYMENT_LINK, ActionType.ATTEMPT_MANUAL_CHARGE}
        )
        assert used <= budget
        allowed = {v.case_id: v.allowed_actions for v in views}
        for action in bundle:
            assert action.action in allowed[action.case_id]
    assert reclaim == ReclaimStrategy(result["pipeline"], result["metadata"]).choose_actions(
        views, budget
    )


def test_training_rows_are_post_collectibility_and_omit_delivery_features():
    assert "service_delivery_status" not in FEATURE_NAMES
    rows = generate_training_rows(13, 80)
    assert all(row.view.backlog_amount_paise > 0 for row in rows)
    assert all(row.view.invoice_count >= 1 for row in rows)
    people = draw_population(SimulationConfig(subscriber_count=40, seed=13))
    for person in people:
        assert collectible_cycle_count(person.first_halt_delivery) == sum(
            1 for status in person.first_halt_delivery if status.value == "delivered"
        )
