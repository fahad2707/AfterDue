"""Benchmark knobs. Does not change the live simulator subscriber cap."""

from pydantic import BaseModel, ConfigDict, Field

from app.simulator.config import SimulationConfig

#: Same ratio as the canonical 100-subscriber / budget-25 demo.
BUDGET_PER_HUNDRED = 25


class EvaluationConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    subscriber_count: int = Field(default=1000, ge=50, le=10_000)
    seed: int = 42
    #: If omitted, scale the canonical 25-per-100 ratio. Not retuned for RECLAIM.
    intervention_budget: int | None = Field(default=None, ge=0)
    bootstrap_samples: int = Field(default=400, ge=50, le=2000)
    include_oracle: bool = True

    def resolved_budget(self) -> int:
        if self.intervention_budget is not None:
            return int(self.intervention_budget)
        return max(1, round(self.subscriber_count * BUDGET_PER_HUNDRED / 100))

    def simulation(self) -> SimulationConfig:
        """Population knobs only. Bypasses the live API subscriber cap."""
        base = SimulationConfig().model_dump()
        base["subscriber_count"] = self.subscriber_count
        base["seed"] = self.seed
        base["intervention_budget"] = self.resolved_budget()
        return SimulationConfig.model_construct(**base)
