from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.domain.enums import (
    ActionType,
    AgentRunStatus,
    RecoveryActionStatus,
    StopReason,
)
from app.domain.money import Paise


class AgentRun(BaseModel):
    model_config = ConfigDict(extra="forbid")

    agent_run_id: str
    run_id: str
    case_id: str
    model_version: str = ""
    policy_version: str = "v1"
    recommended_action: ActionType = ActionType.NO_ACTION
    validated_action: ActionType | None = None
    attempt_number: int = 0
    status: AgentRunStatus = AgentRunStatus.PLANNED
    stop_reason: StopReason | None = None
    next_eligible_at: datetime | None = None
    explanation_source: str = "deterministic"
    synthetic: bool = True
    started_at: datetime
    completed_at: datetime | None = None
    trace: list[dict] = Field(default_factory=list)


class RecoveryAction(BaseModel):
    model_config = ConfigDict(extra="forbid")

    action_id: str
    agent_run_id: str
    run_id: str
    case_id: str
    action: ActionType
    attempt_number: int
    idempotency_key: str
    policy_version: str
    model_version: str = ""
    status: RecoveryActionStatus = RecoveryActionStatus.PLANNED
    outcome: str | None = None
    amount_recovered_paise: Paise = 0
    budget_claimed: bool = False
    stop_reason: StopReason | None = None
    created_at: datetime
    executed_at: datetime | None = None
    synthetic: bool = True
