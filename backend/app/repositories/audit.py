from app.models.documents import AuditLog
from app.repositories.base import Repository, strip_id


class AuditRepository(Repository):
    """Append-only. There is deliberately no update or delete method."""

    @property
    def col(self):
        return self.db["audit_logs"]

    async def append(self, entry: AuditLog) -> None:
        await self.col.insert_one(entry.model_dump())

    async def list_for_subscription(self, subscription_id: str) -> list[AuditLog]:
        cursor = self.col.find({"subscription_id": subscription_id}).sort([("seq", 1)])
        return [AuditLog.model_validate(strip_id(d)) async for d in cursor]
