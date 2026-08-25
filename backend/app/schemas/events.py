from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.domain.enums import EventType, ReasonCode, ServiceDeliveryStatus
from app.domain.money import Paise
from app.schemas.subscriptions import SubscriptionOut


class InvoiceCreatedPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    invoice_id: str
    billing_cycle: str = Field(description="e.g. 2026-02")
    period_start: datetime
    period_end: datetime
    amount_paise: Paise
    currency: str = "INR"
    #: Missing delivery status is UNKNOWN. UNKNOWN fails closed at the gate.
    service_delivery_status: ServiceDeliveryStatus = ServiceDeliveryStatus.UNKNOWN
    waived: bool = False
    merchant_marked_non_collectible: bool = False


class PaymentPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    invoice_id: str | None = None
    amount_paise: Paise | None = None
    failure_reason: str | None = None


class EventIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    event_id: str = Field(description="Caller-supplied. Redelivering it is a no-op.")
    event_type: EventType
    subscription_id: str
    occurred_at: datetime = Field(description="Logical time the event happened.")
    run_id: str | None = Field(
        default=None, description="Defaults to the subscription's run_id."
    )
    payload: dict = Field(default_factory=dict)


class EventOut(BaseModel):
    event_id: str
    run_id: str
    event_type: EventType
    subscription_id: str
    occurred_at: datetime
    received_at: datetime
    processing_status: str
    processed_at: datetime | None
    reason_code: str | None
    payload: dict


class IngestResponse(BaseModel):
    event_id: str
    outcome: str
    reason_code: ReasonCode
    subscription: SubscriptionOut | None = None
