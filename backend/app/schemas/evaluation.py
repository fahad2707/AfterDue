from pydantic import BaseModel, Field

from app.evaluation.config import EvaluationConfig


class EvaluationRequest(EvaluationConfig):
    pass


class EvaluationRunResponse(BaseModel):
    population: dict
    strategies: dict
    intervals: dict = Field(default_factory=dict)
    scenario_breakdown: dict = Field(default_factory=dict)
    diagnostics: list[str] = Field(default_factory=list)
    action_agreement: dict = Field(default_factory=dict)
    action_mix: dict = Field(default_factory=dict)
    family_labels: dict = Field(default_factory=dict)
    limitations: list[str] = Field(default_factory=list)
    synthetic: bool = True
