"""Event ingestion.

The ordering of steps here is load-bearing:

1. resolve the subscription (read only)
2. *claim* the event by inserting it — this is the idempotency gate
3. only then mutate anything

Nothing is written before the claim succeeds, so a duplicate delivery cannot
produce a second state transition or a second audit trail.
"""

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

from pydantic import ValidationError

from app.domain.enums import (
    Actor,
    AuditEventType,
    EventProcessingStatus,
    EventType,
    InvoiceStatus,
    ReasonCode,
    SubscriptionStatus,
)
from app.domain.state_machine import Decision, evaluate, is_lifecycle_event
from app.domain.time import to_storage_precision, utcnow
from app.logging import get_logger
from app.models.documents import Event, HaltEpisode, Invoice, Subscription
from app.repositories.audit import AuditRepository
from app.repositories.events import EventRepository
from app.repositories.invoices import InsertOutcome, InvoiceRepository
from app.repositories.subscriptions import SubscriptionRepository
from app.schemas.events import EventIn, InvoiceCreatedPayload, PaymentPayload
from app.services.audit import AuditTrail
from app.services.recovery_window import RecoveryWindowService

log = get_logger(__name__)


class Outcome(StrEnum):
    PROCESSED = "processed"
    DUPLICATE = "duplicate"
    REJECTED = "rejected"


@dataclass(frozen=True)
class IngestResult:
    event_id: str
    outcome: Outcome
    reason_code: ReasonCode
    subscription: Subscription | None = None


def find_episode_containing(
    subscription: Subscription, moment: datetime
) -> HaltEpisode | None:
    """The halt episode whose window contains `moment`, if any.

    Resolving by time rather than by "the currently open episode" means an
    invoice event that arrives after reactivation is still attributed to the
    halt it was raised during — which is exactly the lineage M2's backlog
    reconstruction depends on.
    """
    for episode in subscription.halt_episodes:
        if moment < episode.halted_at:
            continue
        if episode.reactivated_at is None or moment < episode.reactivated_at:
            return episode
    return None


class EventIngestService:
    def __init__(
        self,
        subscriptions: SubscriptionRepository,
        events: EventRepository,
        invoices: InvoiceRepository,
        audit: AuditRepository,
        recovery: RecoveryWindowService | None = None,
    ) -> None:
        self.subscriptions = subscriptions
        self.events = events
        self.invoices = invoices
        self.trail = AuditTrail(subscriptions, audit)
        self.recovery = recovery

    async def ingest(self, event_in: EventIn) -> IngestResult:
        now = utcnow()
        occurred_at = to_storage_precision(event_in.occurred_at)

        subscription = await self.subscriptions.get(event_in.subscription_id)
        if subscription is None:
            # Nothing to attribute the event to and no audit trail to write it
            # into, so it is refused rather than stored orphaned.
            log.warning(
                "event_unknown_subscription",
                event_id=event_in.event_id,
                subscription_id=event_in.subscription_id,
            )
            return IngestResult(
                event_in.event_id, Outcome.REJECTED, ReasonCode.UNKNOWN_SUBSCRIPTION
            )

        run_id = event_in.run_id or subscription.run_id
        if run_id != subscription.run_id:
            return IngestResult(
                event_in.event_id, Outcome.REJECTED, ReasonCode.RUN_ID_MISMATCH
            )

        event = Event(
            event_id=event_in.event_id,
            run_id=run_id,
            event_type=event_in.event_type,
            subscription_id=event_in.subscription_id,
            occurred_at=occurred_at,
            received_at=now,
            payload=event_in.payload,
        )

        # --- idempotency gate -------------------------------------------------
        if not await self.events.claim(event):
            log.info("event_duplicate", event_id=event.event_id)
            await self.trail.record(
                run_id=run_id,
                subscription_id=subscription.subscription_id,
                event_type=AuditEventType.EVENT_DUPLICATE,
                details={"event_id": event.event_id, "event_type": event.event_type},
            )
            return IngestResult(
                event.event_id,
                Outcome.DUPLICATE,
                ReasonCode.DUPLICATE_EVENT,
                subscription,
            )

        await self.trail.record(
            run_id=run_id,
            subscription_id=subscription.subscription_id,
            event_type=AuditEventType.EVENT_RECEIVED,
            details={
                "event_id": event.event_id,
                "event_type": event.event_type,
                "occurred_at": occurred_at.isoformat(),
            },
        )

        if is_lifecycle_event(event.event_type):
            result = await self._handle_lifecycle(event, subscription, run_id)
        elif event.event_type is EventType.INVOICE_CREATED:
            result = await self._handle_invoice_created(event, subscription, run_id)
        else:
            result = await self._handle_payment(event, subscription, run_id)

        await self.events.mark(
            event.event_id,
            EventProcessingStatus.PROCESSED
            if result.outcome is Outcome.PROCESSED
            else EventProcessingStatus.REJECTED,
            result.reason_code.value,
            utcnow(),
        )

        if result.outcome is Outcome.PROCESSED:
            await self.trail.record(
                run_id=run_id,
                subscription_id=subscription.subscription_id,
                event_type=AuditEventType.EVENT_PROCESSED,
                details={"event_id": event.event_id},
            )
        else:
            await self.trail.record(
                run_id=run_id,
                subscription_id=subscription.subscription_id,
                event_type=AuditEventType.EVENT_REJECTED,
                details={
                    "event_id": event.event_id,
                    "reason_code": result.reason_code.value,
                },
            )

        return result

    # ------------------------------------------------------------------ #
    # lifecycle
    # ------------------------------------------------------------------ #

    async def _handle_lifecycle(
        self, event: Event, subscription: Subscription, run_id: str
    ) -> IngestResult:
        # Out-of-order guard. See docs/architecture.md §6.2 for why this
        # comparison, rather than full event-sourced replay, is the M1 answer.
        # A subscription with no recorded transition yet cannot have a stale
        # event: there is no earlier transition to contradict.
        if (
            subscription.last_state_change_at is not None
            and event.occurred_at < subscription.last_state_change_at
        ):
            log.warning(
                "event_stale",
                event_id=event.event_id,
                occurred_at=event.occurred_at.isoformat(),
                last_state_change_at=subscription.last_state_change_at.isoformat(),
            )
            return IngestResult(
                event.event_id, Outcome.REJECTED, ReasonCode.STALE_EVENT, subscription
            )

        outcome = evaluate(subscription.status, event.event_type)

        if outcome.decision is Decision.REJECTED:
            return IngestResult(
                event.event_id,
                Outcome.REJECTED,
                outcome.reason_code,
                subscription,
            )

        if outcome.decision is Decision.NO_OP:
            await self.trail.record(
                run_id=run_id,
                subscription_id=subscription.subscription_id,
                event_type=AuditEventType.STATE_NO_OP,
                details={"status": subscription.status, "event_id": event.event_id},
            )
            return IngestResult(
                event.event_id, Outcome.PROCESSED, ReasonCode.NO_OP_SAME_STATE, subscription
            )

        assert outcome.to_status is not None
        new_episode: HaltEpisode | None = None
        if outcome.opens_halt_episode:
            new_episode = HaltEpisode(
                episode_id=f"he_{len(subscription.halt_episodes) + 1}",
                halted_at=event.occurred_at,
            )

        updated = await self.subscriptions.apply_transition(
            subscription_id=subscription.subscription_id,
            expected_from=outcome.from_status,
            to_status=outcome.to_status,
            occurred_at=event.occurred_at,
            now=utcnow(),
            open_episode=new_episode,
            close_open_episode=outcome.closes_halt_episode,
        )
        if updated is None:
            return IngestResult(
                event.event_id,
                Outcome.REJECTED,
                ReasonCode.CONCURRENT_MODIFICATION,
                subscription,
            )

        await self.trail.record(
            run_id=run_id,
            subscription_id=updated.subscription_id,
            event_type=AuditEventType.STATE_TRANSITION,
            details={
                "from": outcome.from_status.value,
                "to": outcome.to_status.value,
                "event_id": event.event_id,
            },
        )

        if new_episode is not None:
            await self.trail.record(
                run_id=run_id,
                subscription_id=updated.subscription_id,
                event_type=AuditEventType.HALT_EPISODE_OPENED,
                details={
                    "episode_id": new_episode.episode_id,
                    "halted_at": new_episode.halted_at.isoformat(),
                },
            )

        if outcome.closes_halt_episode:
            closed = next(
                (
                    e
                    for e in updated.halt_episodes
                    if e.reactivated_at == event.occurred_at
                ),
                updated.halt_episodes[-1] if updated.halt_episodes else None,
            )
            await self.trail.record(
                run_id=run_id,
                subscription_id=updated.subscription_id,
                event_type=AuditEventType.HALT_EPISODE_CLOSED,
                details={
                    "episode_id": closed.episode_id if closed else None,
                    "reactivated_at": event.occurred_at.isoformat(),
                    "invoice_count": len(closed.invoice_ids) if closed else 0,
                },
            )
            if self.recovery is not None and closed is not None:
                # The transition is already committed. A failure here is
                # repaired by reconciliation — it must not fail ingestion.
                try:
                    await self.recovery.handle_reactivation(updated, closed)
                except Exception:
                    log.exception(
                        "recovery_window_failed",
                        event_id=event.event_id,
                        subscription_id=updated.subscription_id,
                        halt_episode_id=closed.episode_id,
                    )

        return IngestResult(event.event_id, Outcome.PROCESSED, ReasonCode.OK, updated)

    # ------------------------------------------------------------------ #
    # invoices
    # ------------------------------------------------------------------ #

    async def _handle_invoice_created(
        self, event: Event, subscription: Subscription, run_id: str
    ) -> IngestResult:
        try:
            payload = InvoiceCreatedPayload.model_validate(event.payload)
        except ValidationError:
            return IngestResult(
                event.event_id,
                Outcome.REJECTED,
                ReasonCode.MALFORMED_PAYLOAD,
                subscription,
            )

        episode = find_episode_containing(subscription, event.occurred_at)

        invoice = Invoice(
            invoice_id=payload.invoice_id,
            run_id=run_id,
            subscription_id=subscription.subscription_id,
            billing_cycle=payload.billing_cycle,
            period_start=to_storage_precision(payload.period_start),
            period_end=to_storage_precision(payload.period_end),
            amount_paise=payload.amount_paise,
            currency=payload.currency,
            status=InvoiceStatus.ISSUED_UNPAID,
            halt_episode_id=episode.episode_id if episode else None,
            generated_during_halt=episode is not None,
            created_at=event.occurred_at,
        )

        result = await self.invoices.insert(invoice)
        if result is InsertOutcome.DUPLICATE_INVOICE:
            return IngestResult(
                event.event_id,
                Outcome.REJECTED,
                ReasonCode.DUPLICATE_INVOICE,
                subscription,
            )
        if result is InsertOutcome.DUPLICATE_BILLING_CYCLE:
            return IngestResult(
                event.event_id,
                Outcome.REJECTED,
                ReasonCode.DUPLICATE_BILLING_CYCLE,
                subscription,
            )

        if episode is not None:
            await self.subscriptions.attach_invoice_to_episode(
                subscription.subscription_id, episode.episode_id, invoice.invoice_id
            )

        await self.trail.record(
            run_id=run_id,
            subscription_id=subscription.subscription_id,
            event_type=AuditEventType.INVOICE_RECORDED,
            details={
                "invoice_id": invoice.invoice_id,
                "billing_cycle": invoice.billing_cycle,
                "amount_paise": invoice.amount_paise,
                "halt_episode_id": invoice.halt_episode_id,
                "generated_during_halt": invoice.generated_during_halt,
            },
        )

        refreshed = await self.subscriptions.get(subscription.subscription_id)
        return IngestResult(event.event_id, Outcome.PROCESSED, ReasonCode.OK, refreshed)

    # ------------------------------------------------------------------ #
    # payments
    # ------------------------------------------------------------------ #

    async def _handle_payment(
        self, event: Event, subscription: Subscription, run_id: str
    ) -> IngestResult:
        """Payment events are ledger facts in M1; they do not move subscription
        status. Only the platform's own lifecycle events do that, and inferring
        a halt from a failed payment would duplicate that authority."""
        try:
            payload = PaymentPayload.model_validate(event.payload)
        except ValidationError:
            return IngestResult(
                event.event_id,
                Outcome.REJECTED,
                ReasonCode.MALFORMED_PAYLOAD,
                subscription,
            )

        if event.event_type is EventType.PAYMENT_SUCCEEDED and payload.invoice_id:
            invoice = await self.invoices.get(payload.invoice_id)
            if invoice is None:
                return IngestResult(
                    event.event_id,
                    Outcome.REJECTED,
                    ReasonCode.INVOICE_NOT_FOUND,
                    subscription,
                )
            if await self.invoices.mark_paid(payload.invoice_id):
                await self.trail.record(
                    run_id=run_id,
                    subscription_id=subscription.subscription_id,
                    event_type=AuditEventType.INVOICE_PAID,
                    details={
                        "invoice_id": payload.invoice_id,
                        "amount_paise": invoice.amount_paise,
                    },
                )

        return IngestResult(
            event.event_id, Outcome.PROCESSED, ReasonCode.OK, subscription
        )


def status_of(subscription: Subscription | None) -> SubscriptionStatus | None:
    return subscription.status if subscription else None


__all__ = [
    "Actor",
    "EventIngestService",
    "IngestResult",
    "Outcome",
    "find_episode_containing",
    "status_of",
]
