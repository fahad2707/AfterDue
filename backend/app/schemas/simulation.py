from pydantic import BaseModel, Field

from app.simulator.config import SimulationConfig


class GenerateResponse(BaseModel):
    run_id: str
    world_summary: dict
    synthetic: bool = True


class RunRequest(BaseModel):
    run_id: str
    strategies: list[str] = Field(
        default_factory=lambda: ["naive", "rule_based", "reclaim"]
    )


class RunResponse(BaseModel):
    run_id: str
    seed: int
    strategy_results: dict
    synthetic: bool = True


class SimulationRunOut(BaseModel):
    run_id: str
    seed: int
    synthetic: bool
    status: str
    config: SimulationConfig
    world_summary: dict
    strategy_results: dict
    created_at: str
    completed_at: str | None
    error: str | None = None
