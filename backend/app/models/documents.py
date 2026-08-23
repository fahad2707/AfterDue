"""MongoDB document shapes.

These are the persisted contracts. API request/response shapes live in
`app.schemas` so that changing one does not silently change the other.
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.domain.enums import (
    Actor,
    AuditEventType,
    CardType,
    EventProcessingStatus,
    EventType,
    InvoiceStatus,
    RecoveryCaseStatus,
    SubscriptionStatus,
)
from app.domain.money import Paise


class Customer(BaseModel):
    model_config = ConfigDict(extra="forbid")

    customer_id: str
    run_id: str
    name: str
    risk_flags: list[str] = Field(default_factory=list)
    customer_opted_out: bool = False
    has_active_dispute: bool = False
    #: Synthetic observables for later modelling. Defaults keep M1/M2
    #: documents valid. The oracle's latent intent is NOT stored here.
    historical_payment_success_rate: float = 0.75
    previous_failure_count: int = 0
    previous_halt_count: int = 0
    subscription_age_days: int = 0
    created_at: datetime


class HaltEpisode(BaseModel):
    """One ACTIVE -> HALTED -> ACTIVE cycle.

    A subscription may halt repeatedly, so the halt period cannot be a pair of
    scalar fields on the subscription: the second halt would overwrite the
    first and the invoices raised during it would lose their attribution.
    """

    model_config = ConfigDict(extra="forbid")

    episode_id: str
    halted_at: datetime
    reactivated_at: datetime | None = None
    invoice_ids: list[str] = Field(default_factory=list)

    @property
    def is_open(self) -> bool:
        return self.reactivated_at is None


class Subscription(BaseModel):
    model_config = ConfigDict(extra="forbid")

    subscription_id: str
    run_id: str
    customer_id: str
    status: SubscriptionStatus
    plan_amount_paise: Paise
    currency: str = "INR"
    card_type: CardType
    #: Upper bound the product will treat as chargeable on the mandate.
    #: PRODUCT_DESIGN_ASSUMPTION until Razorpay behaviour is verified.
    mandate_max_amount_paise: Paise
    halt_episodes: list[HaltEpisode] = Field(default_factory=list)

    #: Logical time of the last accepted state change (the event's occurred_at,
    #: not our wall clock). Staleness detection compares against this.
    #:
    #: None until the first transition. Creating a subscription sets its state,
    #: it does not *change* it, so there is nothing yet for an incoming event to
    #: contradict — see INC-007.
    last_state_change_at: datetime | None = None

    #: Monotonic counter backing audit ordering for this subscription.
    audit_seq: int = 0

    created_at: datetime
    updated_at: datetime

    @model_validator(mode="before")
    @classmethod
    def default_mandate_to_plan(cls, data):
        """M1 documents did not store a mandate. Treat the plan amount as the
        cap until an explicit value is written — that is the conservative
        PRODUCT_DESIGN_ASSUMPTION, not a silent raise."""
        if isinstance(data, dict) and data.get("mandate_max_amount_paise") is None:
            data = dict(data)
            data["mandate_max_amount_paise"] = data.get("plan_amount_paise", 0)
        return data

    @property
    def open_halt_episode(self) -> HaltEpisode | None:
        for episode in reversed(self.halt_episodes):
            if episode.is_open:
                return episode
        return None


class Invoice(BaseModel):
    model_config = ConfigDict(extra="forbid")

    invoice_id: str
    run_id: str
    subscription_id: str
    billing_cycle: str
    period_start: datetime
    period_end: datetime
    amount_paise: Paise
    currency: str = "INR"
    status: InvoiceStatus = InvoiceStatus.ISSUED_UNPAID

    #: Authoritative lineage. `generated_during_halt` is a derived convenience
    #: field kept in sync with it, never the source of truth.
    halt_episode_id: str | None = None
    generated_during_halt: bool = False

    created_at: datetime


class Event(BaseModel):
    model_config = ConfigDict(extra="forbid")

    event_id: str
    run_id: str
    event_type: EventType
    subscription_id: str

    #: When the event happened in the payment platform.
    occurred_at: datetime
    #: When RECLAIM received it. These are not the same, and out-of-order
    #: delivery is the reason we keep both.
    received_at: datetime

    payload: dict = Field(default_factory=dict)
    processing_status: EventProcessingStatus = EventProcessingStatus.RECEIVED
    processed_at: datetime | None = None
    reason_code: str | None = None


class AuditLog(BaseModel):
    model_config = ConfigDict(extra="forbid")

    audit_id: str
    run_id: str
    subscription_id: str
    #: Per-subscription monotonic sequence. Timestamps collide at millisecond
    #: resolution during a burst; seq is what actually orders the trail.
    seq: int
    event_type: AuditEventType
    actor: Actor
    details: dict = Field(default_factory=dict)
    ts: datetime


class RecoveryCase(BaseModel):
    """One closed halt episode with an outstanding unpaid backlog.

    Identity is (subscription_id, halt_episode_id). Two cases for the same
    episode would mean we believed the same stranded rupees needed two
    recoveries.
    """

    model_config = ConfigDict(extra="forbid")

    case_id: str
    run_id: str
    subscription_id: str
    customer_id: str
    halt_episode_id: str
    status: RecoveryCaseStatus = RecoveryCaseStatus.OPEN

    invoice_ids: list[str] = Field(default_factory=list)
    invoice_count: int = 0
    backlog_amount_paise: Paise

    oldest_invoice_at: datetime | None = None
    newest_invoice_at: datetime | None = None
    halted_at: datetime
    reactivated_at: datetime
    halt_duration_days: int

    card_type: CardType
    risk_flags: list[str] = Field(default_factory=list)
    policy_version: str

    attempt_count: int = 0
    last_contact_at: datetime | None = None

    created_at: datetime
    updated_at: datetime
