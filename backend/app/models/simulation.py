from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field

from app.simulator.config import SimulationConfig


class SimulationStatus(StrEnum):
    CREATED = "created"
    GENERATED = "generated"
    COMPLETED = "completed"
    FAILED = "failed"


class SimulationRun(BaseModel):
    model_config = ConfigDict(extra="forbid")

    run_id: str
    seed: int
    synthetic: bool = True
    config: SimulationConfig
    status: SimulationStatus = SimulationStatus.CREATED
    created_at: datetime
    completed_at: datetime | None = None
    world_summary: dict = Field(default_factory=dict)
    strategy_results: dict = Field(default_factory=dict)
    error: str | None = None
