from pydantic import BaseModel, Field


class TrainRequest(BaseModel):
    dataset_seed: int = 42
    n_examples: int = Field(default=20_000, ge=200, le=20_000)


class EvaluateRequest(BaseModel):
    dataset_seed: int | None = None
    n_examples: int = Field(default=4_000, ge=200, le=20_000)


class ModelRunOut(BaseModel):
    model_run_id: str
    model_version: str
    model_type: str
    dataset_seed: int
    trained_at: str
    is_active: bool
    feature_schema_hash: str
    n_examples: int = 0
    calibrated: bool = False
    selection_reason: str = ""
    metrics: dict = Field(default_factory=dict)
    business_metrics: dict = Field(default_factory=dict)
    synthetic: bool = True


class ModelAnalysisOut(BaseModel):
    p_no_action: float
    selected_action: str
    p_selected_action: float
    estimated_uplift: float
    expected_incremental_recovery_paise: int
    estimated_recovery_no_action_paise: int
    estimated_recovery_selected_paise: int
    model_version: str
    model_type: str
    candidates: list[dict]
    synthetic: bool = True
    feature_contributions: list[dict] | None = None
