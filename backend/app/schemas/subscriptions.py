from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, computed_field

from app.domain.enums import AuditEventType, CardType, InvoiceStatus, SubscriptionStatus
from app.domain.money import Paise, format_paise


class CustomerIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    customer_id: str
    run_id: str
    name: str
    risk_flags: list[str] = Field(default_factory=list)


class SubscriptionIn(BaseModel):
    """M1 exposes subscription creation over REST rather than as an event.

    The event stream models what the payment platform tells us about an
    existing subscription; provisioning one is our own setup step, and folding
    it into the state machine would add a "no prior state" branch to a table
    that is otherwise exhaustive.
    """

    model_config = ConfigDict(extra="forbid")

    subscription_id: str
    run_id: str
    customer_id: str
    plan_amount_paise: Paise
    card_type: CardType
    currency: str = "INR"
    status: SubscriptionStatus = SubscriptionStatus.ACTIVE
    created_at: datetime | None = None


class HaltEpisodeOut(BaseModel):
    episode_id: str
    halted_at: datetime
    reactivated_at: datetime | None
    invoice_ids: list[str]


class SubscriptionOut(BaseModel):
    subscription_id: str
    run_id: str
    customer_id: str
    status: SubscriptionStatus
    plan_amount_paise: int
    currency: str
    card_type: CardType
    halt_episodes: list[HaltEpisodeOut]
    last_state_change_at: datetime | None
    created_at: datetime
    updated_at: datetime

    @computed_field
    @property
    def plan_amount_display(self) -> str:
        return format_paise(self.plan_amount_paise)


class InvoiceOut(BaseModel):
    invoice_id: str
    run_id: str
    subscription_id: str
    billing_cycle: str
    period_start: datetime
    period_end: datetime
    amount_paise: int
    currency: str
    status: InvoiceStatus
    halt_episode_id: str | None
    generated_during_halt: bool
    created_at: datetime

    @computed_field
    @property
    def amount_display(self) -> str:
        return format_paise(self.amount_paise)


class AuditLogOut(BaseModel):
    audit_id: str
    run_id: str
    subscription_id: str
    seq: int
    event_type: AuditEventType
    actor: str
    details: dict
    ts: datetime
