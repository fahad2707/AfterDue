"""Train challenger models, select on validation, report test once."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime

import numpy as np
import sklearn
from sklearn.calibration import CalibratedClassifierCV, calibration_curve
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    brier_score_loss,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import GroupShuffleSplit
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from app.ml.dataset import DEFAULT_TRAIN_SIZE, generate_training_rows
from app.ml.features import (
    CATEGORICAL_FEATURES,
    NUMERIC_FEATURES,
    build_features,
    feature_schema_hash,
    rows_to_frame,
)

MODEL_VERSION = "m5-v1"


@dataclass
class SplitSets:
    train_idx: np.ndarray
    val_idx: np.ndarray
    test_idx: np.ndarray


@dataclass
class ModelEval:
    model_type: str
    precision: float
    recall: float
    f1: float
    roc_auc: float
    brier: float
    calibrated: bool
    confusion: list[list[int]]
    calibration_bins: dict = field(default_factory=dict)


def _preprocessor() -> ColumnTransformer:
    return ColumnTransformer(
        [
            ("num", StandardScaler(), list(NUMERIC_FEATURES)),
            (
                "cat",
                OneHotEncoder(handle_unknown="ignore", sparse_output=False),
                list(CATEGORICAL_FEATURES),
            ),
        ]
    )


def make_pipeline(model) -> Pipeline:
    return Pipeline([("prep", _preprocessor()), ("clf", model)])


def group_split(groups: list[str], seed: int) -> SplitSets:
    """70/15/15 by group so a synthetic case cannot sit in two splits."""
    idx = np.arange(len(groups))
    gss = GroupShuffleSplit(n_splits=1, test_size=0.15, random_state=seed)
    train_val, test = next(gss.split(idx, groups=groups))
    gss_val = GroupShuffleSplit(n_splits=1, test_size=0.1765, random_state=seed + 1)
    train, val = next(gss_val.split(train_val, groups=[groups[i] for i in train_val]))
    return SplitSets(
        train_idx=train_val[train],
        val_idx=train_val[val],
        test_idx=test,
    )


def _metrics(y_true, proba, *, calibrated: bool, model_type: str) -> ModelEval:
    y_hat = (proba >= 0.5).astype(int)
    tn = int(((y_true == 0) & (y_hat == 0)).sum())
    fp = int(((y_true == 0) & (y_hat == 1)).sum())
    fn = int(((y_true == 1) & (y_hat == 0)).sum())
    tp = int(((y_true == 1) & (y_hat == 1)).sum())
    frac_pos, mean_pred = calibration_curve(y_true, proba, n_bins=10, strategy="quantile")
    auc = float(roc_auc_score(y_true, proba)) if len(set(y_true)) > 1 else 0.5
    return ModelEval(
        model_type=model_type,
        precision=float(precision_score(y_true, y_hat, zero_division=0)),
        recall=float(recall_score(y_true, y_hat, zero_division=0)),
        f1=float(f1_score(y_true, y_hat, zero_division=0)),
        roc_auc=auc,
        brier=float(brier_score_loss(y_true, proba)),
        calibrated=calibrated,
        confusion=[[tn, fp], [fn, tp]],
        calibration_bins={
            "mean_predicted": [float(x) for x in mean_pred],
            "fraction_positive": [float(x) for x in frac_pos],
        },
    )


def _predict_proba(pipeline: Pipeline, frame) -> np.ndarray:
    return pipeline.predict_proba(frame)[:, 1]


def train_and_select(
    dataset_seed: int = 42,
    n_examples: int = DEFAULT_TRAIN_SIZE,
) -> dict:
    rows = generate_training_rows(dataset_seed, n_examples)
    frames = [build_features(row.view, row.action) for row in rows]
    x = rows_to_frame(frames)
    y = np.array([row.recovered for row in rows], dtype=int)
    groups = [row.group_id for row in rows]
    split = group_split(groups, dataset_seed)

    train_groups = {groups[i] for i in split.train_idx}
    val_groups = {groups[i] for i in split.val_idx}
    test_groups = {groups[i] for i in split.test_idx}
    if train_groups & val_groups or train_groups & test_groups or val_groups & test_groups:
        raise RuntimeError("group leakage across splits")

    x_train, y_train = x.iloc[split.train_idx], y[split.train_idx]
    x_val, y_val = x.iloc[split.val_idx], y[split.val_idx]
    x_test, y_test = x.iloc[split.test_idx], y[split.test_idx]

    candidates = {
        "logistic_regression": make_pipeline(
            LogisticRegression(max_iter=800, random_state=dataset_seed)
        ),
        "hist_gradient_boosting": make_pipeline(
            HistGradientBoostingClassifier(max_depth=4, random_state=dataset_seed)
        ),
    }
    val_scores: dict[str, ModelEval] = {}
    for name, pipe in candidates.items():
        pipe.fit(x_train, y_train)
        val_scores[name] = _metrics(
            y_val, _predict_proba(pipe, x_val), calibrated=False, model_type=name
        )

    # Prefer lower Brier (money multiplies probability). AUC is a tie-break.
    selected_name = min(
        val_scores,
        key=lambda n: (val_scores[n].brier, -val_scores[n].roc_auc),
    )
    selected = candidates[selected_name]
    raw_val = val_scores[selected_name]

    # Fit calibration on train only so the validation comparison is held-out.
    try:
        calibrated = CalibratedClassifierCV(selected, method="isotonic", cv=3)
        calibrated.fit(x_train, y_train)
        cal_val = _metrics(
            y_val,
            calibrated.predict_proba(x_val)[:, 1],
            calibrated=True,
            model_type=selected_name,
        )
        use_calibrated = cal_val.brier < raw_val.brier
        cal_note = (
            f"Isotonic calibration kept (val Brier {cal_val.brier:.4f})."
            if use_calibrated
            else (
                f"Raw probabilities kept (calibration val Brier "
                f"{cal_val.brier:.4f} was not better)."
            )
        )
    except ValueError:
        calibrated = selected
        use_calibrated = False
        cal_note = "Calibration skipped (insufficient class support in a fold)."
    final = calibrated if use_calibrated else selected
    selection_reason = (
        f"{selected_name} selected on validation Brier "
        f"({raw_val.brier:.4f} vs "
        + ", ".join(f"{n} {e.brier:.4f}" for n, e in val_scores.items())
        + "). "
        + cal_note
    )

    test_eval = _metrics(
        y_test,
        final.predict_proba(x_test)[:, 1],
        calibrated=use_calibrated,
        model_type=selected_name,
    )
    metadata = {
        "model_version": MODEL_VERSION,
        "model_type": selected_name,
        "calibrated": use_calibrated,
        "trained_at": datetime.now(UTC).isoformat(),
        "dataset_seed": dataset_seed,
        "n_examples": n_examples,
        "sklearn_version": sklearn.__version__,
        "feature_names": list(frames[0].feature_names),
        "feature_schema_hash": feature_schema_hash(),
        "selection_reason": selection_reason,
        "validation": {name: asdict(ev) for name, ev in val_scores.items()},
        "test": asdict(test_eval),
        "split": {
            "train": int(len(split.train_idx)),
            "validation": int(len(split.val_idx)),
            "test": int(len(split.test_idx)),
            "method": "GroupShuffleSplit by world_seed:synthetic_case_key",
        },
        "synthetic": True,
        "collectibility_gate": True,
    }
    metadata["business_metrics"] = {
        "held_out_positive_rate": float(y_test.mean()) if len(y_test) else 0.0,
        "held_out_mean_predicted": float(final.predict_proba(x_test)[:, 1].mean())
        if len(y_test)
        else 0.0,
        "note": (
            "Classification quality on grouped test split. "
            "Strategy economics are measured on simulation runs, not this set."
        ),
    }
    return {"pipeline": final, "metadata": metadata, "test": test_eval}


def evaluate_held_out(
    pipeline,
    dataset_seed: int,
    n_examples: int,
    *,
    calibrated: bool,
    model_type: str,
):
    """Score an existing artifact on a fresh grouped test split. Does not refit."""
    rows = generate_training_rows(dataset_seed, n_examples)
    frames = [build_features(row.view, row.action) for row in rows]
    x = rows_to_frame(frames)
    y = np.array([row.recovered for row in rows], dtype=int)
    groups = [row.group_id for row in rows]
    split = group_split(groups, dataset_seed)
    return _metrics(
        y[split.test_idx],
        _predict_proba(pipeline, x.iloc[split.test_idx]),
        calibrated=calibrated,
        model_type=model_type,
    )
