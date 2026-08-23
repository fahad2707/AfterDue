"""Load and persist the active recovery-model artifact. Not MLflow."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import joblib
from sklearn.pipeline import Pipeline

from app.config import get_settings
from app.ml.errors import FeatureSchemaMismatch, ModelUnavailable
from app.ml.features import FEATURE_NAMES, feature_schema_hash

BACKEND_ROOT = Path(__file__).resolve().parents[2]


def artifact_path(override: str | None = None) -> Path:
    raw = Path(override or get_settings().model_artifact_path)
    if raw.is_absolute():
        return raw
    return BACKEND_ROOT / raw


def save_artifact(pipeline: Pipeline, metadata: dict[str, Any], path: Path | None = None) -> Path:
    dest = path or artifact_path()
    dest.parent.mkdir(parents=True, exist_ok=True)
    payload = {"pipeline": pipeline, "metadata": metadata}
    joblib.dump(payload, dest)
    meta_sidecar = dest.with_suffix(".meta.json")
    meta_sidecar.write_text(_json(metadata), encoding="utf-8")
    return dest


def _json(metadata: dict[str, Any]) -> str:
    import json

    return json.dumps(metadata, indent=2, default=str) + "\n"


def load_artifact(path: Path | None = None) -> tuple[Pipeline, dict[str, Any]]:
    dest = path or artifact_path()
    if not dest.exists():
        raise ModelUnavailable(
            "No valid active recovery model exists. Train one with POST /api/model/train."
        )
    payload = joblib.load(dest)
    if not isinstance(payload, dict) or "pipeline" not in payload or "metadata" not in payload:
        raise ModelUnavailable("Model artifact is missing pipeline or metadata.")
    pipeline = payload["pipeline"]
    metadata = payload["metadata"]
    expected = metadata.get("feature_schema_hash")
    current = feature_schema_hash()
    if expected != current:
        raise FeatureSchemaMismatch(
            f"feature schema mismatch: artifact={expected} current={current}"
        )
    if list(metadata.get("feature_names") or []) != list(FEATURE_NAMES):
        raise FeatureSchemaMismatch("artifact feature_names do not match FEATURE_NAMES")
    return pipeline, metadata


def has_active_model(path: Path | None = None) -> bool:
    try:
        load_artifact(path)
        return True
    except (ModelUnavailable, FeatureSchemaMismatch):
        return False
