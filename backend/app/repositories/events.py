from datetime import datetime

from pymongo.errors import DuplicateKeyError

from app.domain.enums import EventProcessingStatus
from app.models.documents import Event
from app.repositories.base import Repository, strip_id


class EventRepository(Repository):
    @property
    def col(self):
        return self.db["events"]

    async def claim(self, event: Event) -> bool:
        """Attempt to take exclusive ownership of an event_id.

        Returns True if this caller inserted the event and therefore owns
        processing it; False if it already existed.

        The unique index on event_id is the mutex. Two concurrent deliveries of
        the same event both attempt the insert; exactly one succeeds and the
        other raises DuplicateKeyError. This is why ingestion does not
        "check then insert" — between a check and an insert, another worker can
        slip through, and the result is a double state transition.
        """
        try:
            await self.col.insert_one(event.model_dump())
            return True
        except DuplicateKeyError:
            return False

    async def get(self, event_id: str) -> Event | None:
        doc = strip_id(await self.col.find_one({"event_id": event_id}))
        return Event.model_validate(doc) if doc else None

    async def mark(
        self,
        event_id: str,
        status: EventProcessingStatus,
        reason_code: str,
        processed_at: datetime,
    ) -> None:
        await self.col.update_one(
            {"event_id": event_id},
            {
                "$set": {
                    "processing_status": status.value,
                    "reason_code": reason_code,
                    "processed_at": processed_at,
                }
            },
        )

    async def list_for_subscription(self, subscription_id: str) -> list[Event]:
        cursor = self.col.find({"subscription_id": subscription_id}).sort(
            [("occurred_at", 1), ("received_at", 1)]
        )
        return [Event.model_validate(strip_id(d)) async for d in cursor]
