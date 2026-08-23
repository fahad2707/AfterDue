from typing import Any

from pymongo.asynchronous.database import AsyncDatabase


def strip_id(doc: dict[str, Any] | None) -> dict[str, Any] | None:
    """Drop Mongo's `_id`. Document models use extra='forbid', so leaving it in
    would fail validation — and RECLAIM addresses everything by its own
    business identifier, never by ObjectId."""
    if doc is None:
        return None
    doc.pop("_id", None)
    return doc


class Repository:
    def __init__(self, db: AsyncDatabase) -> None:
        self.db = db
