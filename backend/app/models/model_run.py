from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ModelRun(BaseModel):
    model_config = ConfigDict(extra="forbid")

    model_run_id: str
    model_version: str
    model_type: str
    dataset_seed: int
    trained_at: datetime
    is_active: bool = True
    feature_schema_hash: str
    n_examples: int = 0
    calibrated: bool = False
    selection_reason: str = ""
    metrics: dict = Field(default_factory=dict)
    business_metrics: dict = Field(default_factory=dict)
    synthetic: bool = True
