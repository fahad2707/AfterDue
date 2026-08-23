from uuid import uuid4

from app.domain.enums import Actor, AuditEventType
from app.domain.time import utcnow
from app.models.documents import AuditLog
from app.repositories.audit import AuditRepository
from app.repositories.subscriptions import SubscriptionRepository


class AuditTrail:
    """Append-only audit writer.

    Ordering comes from a per-subscription sequence number, not from
    timestamps: a single ingestion writes several entries inside the same
    millisecond, and BSON datetimes cannot separate them.
    """

    def __init__(
        self, subscriptions: SubscriptionRepository, audit: AuditRepository
    ) -> None:
        self.subscriptions = subscriptions
        self.audit = audit

    async def record(
        self,
        *,
        run_id: str,
        subscription_id: str,
        event_type: AuditEventType,
        details: dict | None = None,
        actor: Actor = Actor.EVENT_INGEST,
    ) -> AuditLog:
        seq = await self.subscriptions.next_audit_seq(subscription_id)
        entry = AuditLog(
            audit_id=f"aud_{uuid4().hex[:16]}",
            run_id=run_id,
            subscription_id=subscription_id,
            seq=seq,
            event_type=event_type,
            actor=actor,
            details=details or {},
            ts=utcnow(),
        )
        await self.audit.append(entry)
        return entry
