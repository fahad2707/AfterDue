from fastapi import APIRouter, HTTPException, Query, status

from app.routes.deps import SimRuns
from app.schemas.dashboard import DashboardSummary

router = APIRouter(prefix="/api", tags=["dashboard"])


BASELINE_NAMES = frozenset({"naive", "rule_based"})


def _best_baseline(strategy_results: dict) -> tuple[str | None, int | None, float | None]:
    scored: list[tuple[str, int, float]] = []
    for name, metrics in strategy_results.items():
        if name not in BASELINE_NAMES or not isinstance(metrics, dict):
            continue
        recovered = metrics.get("revenue_recovered_paise")
        if not isinstance(recovered, int):
            continue
        yield_ = metrics.get("recovery_yield")
        scored.append((name, recovered, float(yield_) if yield_ is not None else 0.0))
    if not scored:
        return None, None, None
    name, recovered, yield_ = max(scored, key=lambda row: (row[1], row[2]))
    return name, recovered, yield_


def _reclaim_vs_best(strategy_results: dict) -> int | None:
    reclaim = strategy_results.get("reclaim")
    if not isinstance(reclaim, dict):
        return None
    reclaim_inc = reclaim.get("incremental_revenue_paise")
    if not isinstance(reclaim_inc, int):
        return None
    best = None
    for name in BASELINE_NAMES:
        metrics = strategy_results.get(name)
        if not isinstance(metrics, dict):
            continue
        value = metrics.get("incremental_revenue_paise")
        if isinstance(value, int):
            best = value if best is None else max(best, value)
    if best is None:
        return None
    return reclaim_inc - best


@router.get("/dashboard/summary", response_model=DashboardSummary)
async def dashboard_summary(
    runs: SimRuns,
    run_id: str = Query(description="Required. Metrics are isolated per run."),
):
    record = await runs.get(run_id)
    if record is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "unknown run_id")
    world = record.world_summary or {}
    strategies = record.strategy_results or {}
    name, recovered, yield_ = _best_baseline(strategies)
    config = record.config.model_dump() if hasattr(record.config, "model_dump") else {}
    return DashboardSummary(
        run_id=record.run_id,
        seed=record.seed,
        synthetic=True,
        status=record.status.value if hasattr(record.status, "value") else str(record.status),
        revenue_at_risk_paise=int(world.get("revenue_at_risk_paise") or 0),
        recovery_case_count=int(world.get("recovery_case_count") or 0),
        reactivated_count=int(world.get("reactivated_count") or 0),
        intervention_budget=int(config.get("intervention_budget") or 0),
        best_baseline_name=name,
        best_baseline_recovery_paise=recovered,
        best_baseline_yield=yield_,
        world_summary=world,
        strategy_results=strategies,
        config=config,
        reclaim_vs_best_baseline_paise=_reclaim_vs_best(strategies),
    )
