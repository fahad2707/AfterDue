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
    RECOVERY_WINDOW_OPENED = "RECOVERY_WINDOW_OPENED"
    BACKLOG_RECONSTRUCTED = "BACKLOG_RECONSTRUCTED"
    NO_BACKLOG_FOUND = "NO_BACKLOG_FOUND"
    RECOVERY_CASE_CREATED = "RECOVERY_CASE_CREATED"
    RECOVERY_CASE_DUPLICATE = "RECOVERY_CASE_DUPLICATE"
    POLICY_EVALUATED = "POLICY_EVALUATED"
    RECOVERY_ESCALATED = "RECOVERY_ESCALATED"


class Actor(StrEnum):
    SYSTEM = "system"
    EVENT_INGEST = "event_ingest"
    RECOVERY_WINDOW = "recovery_window"
    RECONCILIATION = "reconciliation"


class RecoveryCaseStatus(StrEnum):
    OPEN = "open"
    ESCALATED = "escalated"
    CLOSED = "closed"


class ActionType(StrEnum):
    NO_ACTION = "no_action"
    SEND_PAYMENT_LINK = "send_payment_link"
    ATTEMPT_MANUAL_CHARGE = "attempt_manual_charge"
    ESCALATE_TO_MERCHANT = "escalate_to_merchant"


class Provenance(StrEnum):
    """Where a policy rule's authority comes from.

    DOCUMENTED_PLATFORM_BEHAVIOR is reserved for independently verified
    platform docs. PRODUCT_DESIGN_ASSUMPTION is an explicit product choice
    that has not been verified against Razorpay. SAFETY_GUARDRAIL is ours
    and does not claim to describe the platform.
    """

    DOCUMENTED_PLATFORM_BEHAVIOR = "DOCUMENTED_PLATFORM_BEHAVIOR"
    PRODUCT_DESIGN_ASSUMPTION = "PRODUCT_DESIGN_ASSUMPTION"
    SAFETY_GUARDRAIL = "SAFETY_GUARDRAIL"


class PolicyReasonCode(StrEnum):
    DOMESTIC_CARD_MANUAL_CHARGE_UNSUPPORTED = (
        "DOMESTIC_CARD_MANUAL_CHARGE_UNSUPPORTED"
    )
    MANDATE_CAP_EXCEEDED = "MANDATE_CAP_EXCEEDED"
    RISK_FLAG_PRESENT = "RISK_FLAG_PRESENT"
    ACTIVE_DISPUTE = "ACTIVE_DISPUTE"
    CUSTOMER_OPTED_OUT = "CUSTOMER_OPTED_OUT"
    MAX_ATTEMPTS_REACHED = "MAX_ATTEMPTS_REACHED"
    CONTACT_COOLDOWN_ACTIVE = "CONTACT_COOLDOWN_ACTIVE"


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
