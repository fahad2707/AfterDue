from pydantic import BaseModel, ConfigDict, Field


class CaseExplanation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    summary: str
    why_case_exists: str
    recommended_action_explanation: str
    policy_constraints: list[str] = Field(default_factory=list)
    economic_reasoning: str
    uncertainty_note: str
    synthetic_disclaimer: str = (
        "SYNTHETIC SIMULATION — NOT PRODUCTION DATA. "
        "Figures are model estimates, not guaranteed recovery."
    )


class ExtractionEvidence(BaseModel):
    model_config = ConfigDict(extra="forbid")

    field: str
    span: str
    confidence: float = Field(ge=0.0, le=1.0)


class ExtractionProposal(BaseModel):
    model_config = ConfigDict(extra="forbid")

    has_dispute: bool | None = None
    customer_opted_out: bool | None = None
    risk_signals: list[str] = Field(default_factory=list)
    evidence: list[ExtractionEvidence] = Field(default_factory=list)
    uncertainty_note: str = ""


class QAAnswer(BaseModel):
    model_config = ConfigDict(extra="forbid")

    answer: str
    grounding: list[str] = Field(default_factory=list)
    insufficient_information: bool = False
