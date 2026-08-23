"""Index definitions and bootstrap.

Several of these indexes are not performance hints — they are correctness
constraints. Where a unique index prevents a class of financial bug, that is
noted, because dropping one of those "for speed" later would be a mistake.
"""

from pymongo import ASCENDING, IndexModel
from pymongo.asynchronous.database import AsyncDatabase

from app.logging import get_logger

log = get_logger(__name__)

INDEXES: dict[str, list[IndexModel]] = {
    "customers": [
        IndexModel([("customer_id", ASCENDING)], name="uq_customer_id", unique=True),
    ],
    "subscriptions": [
        IndexModel(
            [("subscription_id", ASCENDING)], name="uq_subscription_id", unique=True
        ),
        IndexModel([("run_id", ASCENDING), ("status", ASCENDING)], name="run_status"),
    ],
    "invoices": [
        IndexModel([("invoice_id", ASCENDING)], name="uq_invoice_id", unique=True),
        # Correctness: one invoice per subscription per billing cycle. Makes
        # double-billing a cycle impossible rather than merely unlikely.
        IndexModel(
            [("subscription_id", ASCENDING), ("billing_cycle", ASCENDING)],
            name="uq_subscription_billing_cycle",
            unique=True,
        ),
        # Serves backlog reconstruction in M2.
        IndexModel(
            [
                ("subscription_id", ASCENDING),
                ("status", ASCENDING),
                ("period_start", ASCENDING),
            ],
            name="subscription_status_period",
        ),
    ],
    "events": [
        # Correctness: this index *is* the idempotency mechanism. Ingestion
        # claims an event by inserting it; a duplicate delivery loses the
        # insert and is never processed twice.
        IndexModel([("event_id", ASCENDING)], name="uq_event_id", unique=True),
        IndexModel(
            [("subscription_id", ASCENDING), ("occurred_at", ASCENDING)],
            name="subscription_occurred",
        ),
        IndexModel(
            [("run_id", ASCENDING), ("received_at", ASCENDING)], name="run_received"
        ),
    ],
    "audit_logs": [
        # Correctness: guarantees the per-subscription sequence has no gaps
        # from double-writes and no two entries claiming the same position.
        IndexModel(
            [("subscription_id", ASCENDING), ("seq", ASCENDING)],
            name="uq_subscription_seq",
            unique=True,
        ),
        IndexModel([("run_id", ASCENDING), ("ts", ASCENDING)], name="run_ts"),
    ],
}


async def ensure_indexes(db: AsyncDatabase) -> dict[str, list[str]]:
    """Create every index. Idempotent — safe to run on every startup."""
    created: dict[str, list[str]] = {}
    for collection_name, models in INDEXES.items():
        names = await db[collection_name].create_indexes(models)
        created[collection_name] = names
    log.info("indexes_ensured", collections=list(created))
    return created
