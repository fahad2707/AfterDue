from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, computed_field

from app.domain.enums import CardType, RecoveryCaseStatus
from app.domain.money import format_paise
from app.domain.policy import PolicyContext, PolicyDecision
from app.schemas.subscriptions import HaltEpisodeOut, InvoiceOut


class RecoveryCaseOut(BaseModel):
    case_id: str
    run_id: str
    subscription_id: str
    customer_id: str
    synthetic_case_key: str | None = None
    synthetic_customer_key: str | None = None
    halt_episode_id: str
    status: RecoveryCaseStatus
    invoice_ids: list[str]
    invoice_count: int
    backlog_amount_paise: int
    oldest_invoice_at: datetime | None
    newest_invoice_at: datetime | None
    halted_at: datetime
    reactivated_at: datetime
    halt_duration_days: int
    card_type: CardType
    risk_flags: list[str]
    historical_payment_success_rate: float = 0.75
    previous_failure_count: int = 0
    previous_halt_count: int = 0
    subscription_age_days: int = 0
    customer_opted_out: bool = False
    has_active_dispute: bool = False
    policy_version: str
    attempt_count: int
    last_contact_at: datetime | None
    created_at: datetime
    updated_at: datetime
    #: Filled at read time so the queue can show a name and policy state.
    customer_name: str = ""
    policy_status: str = "eligible"
    allowed_actions: list[str] = Field(default_factory=list)
    blocked_actions: list[str] = Field(default_factory=list)
    requires_escalation: bool = False
    stop: bool = False

    @computed_field
    @property
    def backlog_amount_display(self) -> str:
        return format_paise(self.backlog_amount_paise)


class RecoveryCaseDetail(BaseModel):
    case: RecoveryCaseOut
    invoices: list[InvoiceOut]
    policy: PolicyDecision
    customer_name: str = ""
    subscription_status: str = ""
    subscription_created_at: datetime | None = None
    halt_episodes: list[HaltEpisodeOut] = Field(default_factory=list)


class PolicyConfigOut(BaseModel):
    policy_version: str
    max_attempts: int
    contact_cooldown_hours: int
    actions: list[str]
    rules: list[dict]
    reason_codes: list[str]
    provenance_values: list[str]
    synthetic: bool = True


class ReconcileReportOut(BaseModel):
    examined_episodes: int
    created_case_ids: list[str]
    already_present: int
    skipped_no_backlog: int


class PolicyEvaluateIn(PolicyContext):
    """Dry-run input. Same shape as PolicyContext; no persistence."""

    model_config = ConfigDict(extra="forbid")
