from enum import StrEnum


class SubscriptionStatus(StrEnum):
    ACTIVE = "active"
    PENDING = "pending"
    HALTED = "halted"


class CardType(StrEnum):
    DOMESTIC = "domestic"
    INTERNATIONAL = "international"


class EventType(StrEnum):
    SUBSCRIPTION_PENDING = "subscription.pending"
    SUBSCRIPTION_HALTED = "subscription.halted"
    SUBSCRIPTION_ACTIVATED = "subscription.activated"
    INVOICE_CREATED = "invoice.created"
    PAYMENT_FAILED = "payment.failed"
    PAYMENT_SUCCEEDED = "payment.succeeded"


#: Events that drive the subscription state machine. Everything else is
#: recorded against the ledger without changing subscription status.
LIFECYCLE_EVENTS = frozenset(
    {
        EventType.SUBSCRIPTION_PENDING,
        EventType.SUBSCRIPTION_HALTED,
        EventType.SUBSCRIPTION_ACTIVATED,
    }
)


class InvoiceStatus(StrEnum):
    PAID = "paid"
    ISSUED_UNPAID = "issued_unpaid"


class EventProcessingStatus(StrEnum):
    RECEIVED = "received"
    PROCESSED = "processed"
    REJECTED = "rejected"


class AuditEventType(StrEnum):
    EVENT_RECEIVED = "EVENT_RECEIVED"
    EVENT_DUPLICATE = "EVENT_DUPLICATE"
    EVENT_REJECTED = "EVENT_REJECTED"
    EVENT_PROCESSED = "EVENT_PROCESSED"
    STATE_TRANSITION = "STATE_TRANSITION"
    STATE_NO_OP = "STATE_NO_OP"
    HALT_EPISODE_OPENED = "HALT_EPISODE_OPENED"
    HALT_EPISODE_CLOSED = "HALT_EPISODE_CLOSED"
    INVOICE_RECORDED = "INVOICE_RECORDED"
    INVOICE_PAID = "INVOICE_PAID"


class Actor(StrEnum):
    SYSTEM = "system"
    EVENT_INGEST = "event_ingest"


class ReasonCode(StrEnum):
    """Machine-readable outcome codes. Every rejection carries exactly one."""

    OK = "OK"
    DUPLICATE_EVENT = "DUPLICATE_EVENT"
    UNKNOWN_SUBSCRIPTION = "UNKNOWN_SUBSCRIPTION"
    ILLEGAL_TRANSITION = "ILLEGAL_TRANSITION"
    STALE_EVENT = "STALE_EVENT"
    CONCURRENT_MODIFICATION = "CONCURRENT_MODIFICATION"
    NO_OP_SAME_STATE = "NO_OP_SAME_STATE"
    DUPLICATE_BILLING_CYCLE = "DUPLICATE_BILLING_CYCLE"
    DUPLICATE_INVOICE = "DUPLICATE_INVOICE"
    INVOICE_NOT_FOUND = "INVOICE_NOT_FOUND"
    MALFORMED_PAYLOAD = "MALFORMED_PAYLOAD"
    RUN_ID_MISMATCH = "RUN_ID_MISMATCH"
