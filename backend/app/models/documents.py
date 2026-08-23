"""MongoDB document shapes.

These are the persisted contracts. API request/response shapes live in
`app.schemas` so that changing one does not silently change the other.
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.domain.enums import (
    Actor,
    AuditEventType,
    CardType,
    EventProcessingStatus,
    EventType,
    InvoiceStatus,
    SubscriptionStatus,
)
from app.domain.money import Paise


class Customer(BaseModel):
    model_config = ConfigDict(extra="forbid")

    customer_id: str
    run_id: str
    name: str
    risk_flags: list[str] = Field(default_factory=list)
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
