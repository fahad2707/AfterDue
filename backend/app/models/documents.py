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
    CollectibilityReasonCode,
    CollectibilityStatus,
    EventProcessingStatus,
    EventType,
    InvoiceStatus,
    RecoveryCaseStatus,
    ServiceDeliveryStatus,
    SubscriptionStatus,
)
from app.domain.money import Paise


class Customer(BaseModel):
    model_config = ConfigDict(extra="forbid")

    customer_id: str
    run_id: str
    #: Seed-stable simulation identity. None on hand-seeded M1/M2 documents.
    synthetic_customer_key: str | None = None
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

    #: Service entitlement. Missing ingest data is UNKNOWN (fail closed).
    service_delivery_status: ServiceDeliveryStatus = ServiceDeliveryStatus.UNKNOWN
    waived: bool = False
    merchant_marked_non_collectible: bool = False
    #: Written by the collectibility engine at recovery-window time.
    collectibility_status: CollectibilityStatus = CollectibilityStatus.REVIEW_REQUIRED
    collectibility_reason_codes: list[CollectibilityReasonCode] = Field(
        default_factory=lambda: [CollectibilityReasonCode.SERVICE_DELIVERY_UNKNOWN]
    )

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
    #: Seed-stable simulation identities. None on hand-seeded M1/M2 cases.
    synthetic_case_key: str | None = None
    synthetic_customer_key: str | None = None
    halt_episode_id: str
    status: RecoveryCaseStatus = RecoveryCaseStatus.OPEN
    collectibility_status: CollectibilityStatus = CollectibilityStatus.COLLECTIBLE

    invoice_ids: list[str] = Field(default_factory=list)
    invoice_count: int = 0
    #: Compatibility/economic field. MUST equal collectible_amount_paise.
    backlog_amount_paise: Paise
    historical_unpaid_amount_paise: Paise = 0
    collectible_amount_paise: Paise = 0
    review_required_amount_paise: Paise = 0
    not_collectible_amount_paise: Paise = 0
    collectible_invoice_ids: list[str] = Field(default_factory=list)
    review_required_invoice_ids: list[str] = Field(default_factory=list)
    not_collectible_invoice_ids: list[str] = Field(default_factory=list)

    oldest_invoice_at: datetime | None = None
    newest_invoice_at: datetime | None = None
    halted_at: datetime
    reactivated_at: datetime
    halt_duration_days: int

    card_type: CardType
    risk_flags: list[str] = Field(default_factory=list)
    #: Customer snapshot at case open. Defaults keep M1/M2 documents valid.
    historical_payment_success_rate: float = 0.75
    previous_failure_count: int = 0
    previous_halt_count: int = 0
    subscription_age_days: int = 0
    customer_opted_out: bool = False
    has_active_dispute: bool = False
    policy_version: str

    attempt_count: int = 0
    last_contact_at: datetime | None = None
    #: Full-backlog recovery only. Partial invoice settlement is not modeled.
    amount_recovered_paise: Paise = 0

    created_at: datetime
    updated_at: datetime

    @model_validator(mode="before")
    @classmethod
    def default_collectibility_fields(cls, data):
        """Pre-gate documents stored only backlog_amount_paise.

        Those worlds treated unpaid halt invoices as collectible. New fields
        default from that amount so old fixtures remain valid. After the
        collectibility gate, callers must set the fields explicitly.
        """
        if not isinstance(data, dict):
            return data
        data = dict(data)
        backlog = data.get("backlog_amount_paise", 0)
        if data.get("collectible_amount_paise") is None:
            data["collectible_amount_paise"] = backlog
        if data.get("historical_unpaid_amount_paise") is None:
            data["historical_unpaid_amount_paise"] = backlog
        data.setdefault("review_required_amount_paise", 0)
        data.setdefault("not_collectible_amount_paise", 0)
        ids = data.get("invoice_ids") or []
        if not data.get("collectible_invoice_ids"):
            data["collectible_invoice_ids"] = list(ids)
        data.setdefault("review_required_invoice_ids", [])
        data.setdefault("not_collectible_invoice_ids", [])
        return data

    @model_validator(mode="after")
    def backlog_equals_collectible(self):
        if self.backlog_amount_paise != self.collectible_amount_paise:
            raise ValueError(
                "backlog_amount_paise must equal collectible_amount_paise"
            )
        return self

    def evaluated_invoice_ids(self) -> list[str]:
        seen: list[str] = []
        for group in (
            self.collectible_invoice_ids or self.invoice_ids,
            self.review_required_invoice_ids,
            self.not_collectible_invoice_ids,
        ):
            for invoice_id in group:
                if invoice_id not in seen:
                    seen.append(invoice_id)
        return seen

    def is_strategy_eligible(self) -> bool:
        """True only for established collectible receivables.

        REVIEW_REQUIRED is not an economic case. CLOSED is done.
        ESCALATED remains eligible so every strategy sees the same universe;
        policy, not collectibility, restricts those actions.
        """
        if self.backlog_amount_paise != self.collectible_amount_paise:
            raise ValueError(
                "backlog_amount_paise must equal collectible_amount_paise"
            )
        if self.status in (
            RecoveryCaseStatus.REVIEW_REQUIRED,
            RecoveryCaseStatus.CLOSED,
        ):
            return False
        return self.collectible_amount_paise > 0
