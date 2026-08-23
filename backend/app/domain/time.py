from datetime import UTC, datetime


def utcnow() -> datetime:
    return to_storage_precision(datetime.now(UTC))


def to_storage_precision(dt: datetime) -> datetime:
    """Truncate to milliseconds and normalise to UTC.

    BSON datetimes hold milliseconds. Without truncating on the way in, a value
    compared in memory against the same value read back from Mongo can differ
    by microseconds — which matters because staleness detection compares
    `occurred_at` against a stored `last_state_change_at`.
    """
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    dt = dt.astimezone(UTC)
    return dt.replace(microsecond=(dt.microsecond // 1000) * 1000)
