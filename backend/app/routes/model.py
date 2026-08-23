from datetime import datetime
from uuid import uuid4

from fastapi import APIRouter, HTTPException, status

from app.domain.time import utcnow
from app.ml.errors import FeatureSchemaMismatch, ModelUnavailable
from app.ml.explain import logistic_contributions
from app.ml.features import feature_schema_hash
from app.ml.registry import load_artifact, save_artifact
from app.ml.train import train_and_select
from app.models.model_run import ModelRun
from app.routes.deps import ModelRuns
from app.schemas.model import EvaluateRequest, ModelRunOut, TrainRequest

router = APIRouter(prefix="/api/model", tags=["model"])


def _out(run: ModelRun) -> ModelRunOut:
    trained = run.trained_at
    return ModelRunOut(
        model_run_id=run.model_run_id,
        model_version=run.model_version,
        model_type=run.model_type,
        dataset_seed=run.dataset_seed,
        trained_at=trained.isoformat() if isinstance(trained, datetime) else str(trained),
        is_active=run.is_active,
        feature_schema_hash=run.feature_schema_hash,
        n_examples=run.n_examples,
        calibrated=run.calibrated,
        selection_reason=run.selection_reason,
        metrics=run.metrics,
        business_metrics=run.business_metrics,
        synthetic=True,
    )


def _artifact_out(metadata: dict) -> ModelRunOut:
    return ModelRunOut(
        model_run_id=str(metadata.get("model_run_id") or "artifact"),
        model_version=str(metadata.get("model_version") or ""),
        model_type=str(metadata.get("model_type") or ""),
        dataset_seed=int(metadata.get("dataset_seed") or 0),
        trained_at=str(metadata.get("trained_at") or ""),
        is_active=True,
        feature_schema_hash=str(metadata.get("feature_schema_hash") or ""),
        n_examples=int(metadata.get("n_examples") or 0),
        calibrated=bool(metadata.get("calibrated")),
        selection_reason=str(metadata.get("selection_reason") or ""),
        metrics=metadata.get("test") or metadata.get("metrics") or {},
        business_metrics=metadata.get("business_metrics") or {},
        synthetic=True,
    )


@router.post("/train", response_model=ModelRunOut)
async def train_model(body: TrainRequest, model_runs: ModelRuns):
    result = train_and_select(dataset_seed=body.dataset_seed, n_examples=body.n_examples)
    metadata = result["metadata"]
    model_run_id = f"model_{body.dataset_seed}_{uuid4().hex[:8]}"
    metadata["model_run_id"] = model_run_id
    contributions = logistic_contributions(result["pipeline"], metadata["model_type"])
    if contributions:
        metadata["feature_contributions"] = contributions
    save_artifact(result["pipeline"], metadata)
    record = ModelRun(
        model_run_id=model_run_id,
        model_version=metadata["model_version"],
        model_type=metadata["model_type"],
        dataset_seed=body.dataset_seed,
        trained_at=utcnow(),
        is_active=True,
        feature_schema_hash=metadata["feature_schema_hash"],
        n_examples=body.n_examples,
        calibrated=bool(metadata.get("calibrated")),
        selection_reason=str(metadata.get("selection_reason") or ""),
        metrics=metadata.get("test") or {},
        business_metrics={
            "selection_reason": metadata.get("selection_reason"),
            "validation": metadata.get("validation"),
            "split": metadata.get("split"),
        },
    )
    await model_runs.insert(record)
    return _out(record)


@router.post("/evaluate", response_model=ModelRunOut)
async def evaluate_model(body: EvaluateRequest, model_runs: ModelRuns):
    try:
        pipeline, metadata = load_artifact()
    except ModelUnavailable as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, str(exc)) from exc
    except FeatureSchemaMismatch as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, str(exc)) from exc
    seed = body.dataset_seed if body.dataset_seed is not None else int(metadata["dataset_seed"])
    from app.ml.train import evaluate_held_out

    test = evaluate_held_out(
        pipeline,
        seed,
        body.n_examples,
        calibrated=bool(metadata.get("calibrated")),
        model_type=str(metadata.get("model_type")),
    )
    payload = _artifact_out({**metadata, "test": test.__dict__})
    active = await model_runs.get_active()
    if active:
        payload.model_run_id = active.model_run_id
        payload.metrics = test.__dict__
    return payload


@router.get("/metrics", response_model=ModelRunOut)
async def model_metrics(model_runs: ModelRuns):
    active = await model_runs.get_active()
    if active:
        return _out(active)
    try:
        _, metadata = load_artifact()
    except (ModelUnavailable, FeatureSchemaMismatch) as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc)) from exc
    return _artifact_out(metadata)


@router.get("/active", response_model=ModelRunOut)
async def active_model(model_runs: ModelRuns):
    active = await model_runs.get_active()
    if active:
        return _out(active)
    try:
        _, metadata = load_artifact()
    except (ModelUnavailable, FeatureSchemaMismatch) as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc)) from exc
    return _artifact_out(metadata)


@router.get("/schema")
async def model_schema():
    return {"feature_schema_hash": feature_schema_hash(), "synthetic": True}
