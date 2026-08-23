from datetime import datetime

from fastapi import APIRouter, HTTPException, status

from app.routes.deps import SimRunner, SimRuns
from app.schemas.simulation import (
    GenerateResponse,
    RunRequest,
    RunResponse,
    SimulationRunOut,
)
from app.simulator.config import SimulationConfig

router = APIRouter(prefix="/api", tags=["simulator"])


def _out(run) -> SimulationRunOut:
    return SimulationRunOut(
        run_id=run.run_id,
        seed=run.seed,
        synthetic=True,
        status=run.status.value if hasattr(run.status, "value") else run.status,
        config=run.config,
        world_summary=run.world_summary,
        strategy_results=run.strategy_results,
        created_at=run.created_at.isoformat()
        if isinstance(run.created_at, datetime)
        else str(run.created_at),
        completed_at=run.completed_at.isoformat()
        if run.completed_at
        else None,
        error=run.error,
    )


@router.post("/simulator/generate", response_model=GenerateResponse)
async def generate_world(config: SimulationConfig, runner: SimRunner):
    run_id, summary = await runner.generate(config)
    return GenerateResponse(
        run_id=run_id, world_summary=summary.__dict__, synthetic=True
    )


@router.post("/simulator/run", response_model=RunResponse)
async def run_strategies(body: RunRequest, runner: SimRunner, runs: SimRuns):
    record = await runs.get(body.run_id)
    if record is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "unknown run_id")
    results = await runner.run_strategies(body.run_id, body.strategies)
    return RunResponse(
        run_id=body.run_id,
        seed=record.seed,
        strategy_results={name: m.__dict__ for name, m in results.items()},
        synthetic=True,
    )


@router.get("/runs", response_model=list[SimulationRunOut])
async def list_runs(runs: SimRuns):
    return [_out(r) for r in await runs.list_recent()]


@router.get("/runs/{run_id}", response_model=SimulationRunOut)
async def get_run(run_id: str, runs: SimRuns):
    record = await runs.get(run_id)
    if record is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "unknown run_id")
    return _out(record)
