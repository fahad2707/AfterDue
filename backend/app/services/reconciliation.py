"""Repair missing recovery cases.

If HALTED → ACTIVE committed and then the process died before
create_if_absent, the subscription is correctly ACTIVE and the case is
missing. This function is safe to run more than once: create_if_absent uses
the unique episode index, so a second pass is a no-op.
"""

from dataclasses import dataclass

from app.domain.enums import Actor
from app.logging import get_logger
from app.repositories.customers import CustomerRepository
from app.repositories.invoices import InvoiceRepository
from app.repositories.recovery_cases import RecoveryCaseRepository
from app.repositories.subscriptions import SubscriptionRepository
from app.services.audit import AuditTrail
from app.services.backlog_builder import BacklogBuilder
from app.services.recovery_window import RecoveryWindowResult, RecoveryWindowService

log = get_logger(__name__)


@dataclass(frozen=True)
class ReconciliationReport:
    examined_episodes: int
    created_case_ids: list[str]
    already_present: int
    skipped_no_backlog: int


class ReconciliationService:
    def __init__(
        self,
        subscriptions: SubscriptionRepository,
        invoices: InvoiceRepository,
        customers: CustomerRepository,
        cases: RecoveryCaseRepository,
        trail: AuditTrail,
    ) -> None:
        self.subscriptions = subscriptions
        self.cases = cases
        self.window = RecoveryWindowService(
            customers=customers,
            cases=cases,
            backlog=BacklogBuilder(invoices),
            trail=trail,
            actor=Actor.RECONCILIATION,
        )

    async def reconcile(self) -> ReconciliationReport:
        created: list[str] = []
        already = 0
        skipped = 0
        examined = 0

        for subscription in await self.subscriptions.list_with_closed_halt_episodes():
            for episode in subscription.halt_episodes:
                if episode.reactivated_at is None:
                    continue
                examined += 1
                existing = await self.cases.get_by_episode(
                    subscription.subscription_id, episode.episode_id
                )
                if existing is not None:
                    already += 1
                    continue

                result: RecoveryWindowResult = await self.window.handle_reactivation(
                    subscription, episode
                )
                if result.created and result.case is not None:
                    created.append(result.case.case_id)
                    log.info(
                        "reconciliation_created_case",
                        case_id=result.case.case_id,
                        subscription_id=subscription.subscription_id,
                    )
                else:
                    skipped += 1

        return ReconciliationReport(
            examined_episodes=examined,
            created_case_ids=created,
            already_present=already,
            skipped_no_backlog=skipped,
        )
