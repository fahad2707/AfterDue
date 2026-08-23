from pydantic import BaseModel, Field


class DashboardSummary(BaseModel):
    run_id: str
    seed: int
    synthetic: bool = True
    status: str
    revenue_at_risk_paise: int
    recovery_case_count: int
    reactivated_count: int
    intervention_budget: int
    best_baseline_name: str | None = None
    best_baseline_recovery_paise: int | None = None
    best_baseline_yield: float | None = None
    world_summary: dict = Field(default_factory=dict)
    strategy_results: dict = Field(default_factory=dict)
    config: dict = Field(default_factory=dict)
    reclaim_vs_best_baseline_paise: int | None = None
