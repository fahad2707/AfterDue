"""Open a recovery window after HALTED → ACTIVE.

State transition is already committed when this runs. A failure here must
not undo that transition — the ledger is authoritative, and reconciliation
repairs a missing case. See docs/architecture.md §7.

Collectibility runs after unpaid reconstruction and before case economics.
Invoice existence is not proof of collectibility.
"""

from dataclasses import dataclass

from app.config import get_settings
from app.domain.collectibility import (
    CollectibilityDecision,
    CollectibleBacklogResult,
    evaluate_collectibility_for_invoices,
)
from app.domain.enums import (
    Actor,
    AuditEventType,
    CollectibilityStatus,
    RecoveryCaseStatus,
)
from app.domain.policy import PolicyContext, PolicyDecision
from app.domain.time import utcnow
from app.logging import get_logger
from app.models.documents import HaltEpisode, RecoveryCase, Subscription
from app.policy import evaluate_v1
from app.repositories.customers import CustomerRepository
from app.repositories.recovery_cases import RecoveryCaseRepository
from app.services.audit import AuditTrail
from app.services.backlog_builder import BacklogBuilder

log = get_logger(__name__)

_INVOICE_AUDIT = {
    CollectibilityStatus.COLLECTIBLE: AuditEventType.INVOICE_MARKED_COLLECTIBLE,
    CollectibilityStatus.NOT_COLLECTIBLE: AuditEventType.INVOICE_EXCLUDED_NON_COLLECTIBLE,
    CollectibilityStatus.REVIEW_REQUIRED: AuditEventType.INVOICE_REVIEW_REQUIRED,
}


@dataclass(frozen=True)
class RecoveryWindowResult:
    case: RecoveryCase | None
    created: bool
    decision: PolicyDecision | None


def case_id_for(subscription_id: str, halt_episode_id: str) -> str:
    return f"case_{subscription_id}_{halt_episode_id}"


class RecoveryWindowService:
    def __init__(
        self,
        customers: CustomerRepository,
        cases: RecoveryCaseRepository,
        backlog: BacklogBuilder,
        trail: AuditTrail,
        actor: Actor = Actor.RECOVERY_WINDOW,
    ) -> None:
        self.customers = customers
        self.cases = cases
        self.backlog = backlog
        self.trail = trail
        self.actor = actor

    async def handle_reactivation(
        self, subscription: Subscription, episode: HaltEpisode
    ) -> RecoveryWindowResult:
        if episode.reactivated_at is None:
            raise ValueError(
                f"episode {episode.episode_id} is still open; no recovery window"
            )

        await self.trail.record(
            run_id=subscription.run_id,
            subscription_id=subscription.subscription_id,
            event_type=AuditEventType.RECOVERY_WINDOW_OPENED,
            details={"halt_episode_id": episode.episode_id},
            actor=self.actor,
        )

        historical = await self.backlog.for_episode(subscription, episode.episode_id)

        if not historical.has_outstanding:
            await self.trail.record(
                run_id=subscription.run_id,
                subscription_id=subscription.subscription_id,
                event_type=AuditEventType.NO_BACKLOG_FOUND,
                details={"halt_episode_id": episode.episode_id},
                actor=self.actor,
            )
            return RecoveryWindowResult(None, False, None)

        await self.trail.record(
            run_id=subscription.run_id,
            subscription_id=subscription.subscription_id,
            event_type=AuditEventType.BACKLOG_RECONSTRUCTED,
            details={
                "halt_episode_id": episode.episode_id,
                "invoice_count": historical.invoice_count,
                "invoice_ids": historical.invoice_ids,
                "historical_unpaid_amount_paise": historical.backlog_amount_paise,
            },
            actor=self.actor,
        )

        invoices = await self.backlog.invoices.list_for_ids(historical.invoice_ids)
        by_id = {invoice.invoice_id: invoice for invoice in invoices}
        ordered = [by_id[i] for i in historical.invoice_ids if i in by_id]
        gated = evaluate_collectibility_for_invoices(ordered)
        await self._persist_and_audit_collectibility(
            subscription, episode.episode_id, gated
        )

        if gated.collectible_amount_paise > 0:
            status = RecoveryCaseStatus.OPEN
            collectibility_status = CollectibilityStatus.COLLECTIBLE
        elif gated.review_required_amount_paise > 0:
            status = RecoveryCaseStatus.REVIEW_REQUIRED
            collectibility_status = CollectibilityStatus.REVIEW_REQUIRED
        else:
            return RecoveryWindowResult(None, False, None)

        customer = await self.customers.get(subscription.customer_id)
        risk_flags = customer.risk_flags if customer else []

        now = utcnow()
        collectible_ids = list(gated.collectible_invoice_ids)
        draft = RecoveryCase(
            case_id=case_id_for(subscription.subscription_id, episode.episode_id),
            run_id=subscription.run_id,
            subscription_id=subscription.subscription_id,
            customer_id=subscription.customer_id,
            halt_episode_id=episode.episode_id,
            status=status,
            collectibility_status=collectibility_status,
            invoice_ids=collectible_ids,
            invoice_count=len(collectible_ids),
            backlog_amount_paise=gated.collectible_amount_paise,
            historical_unpaid_amount_paise=gated.historical_unpaid_amount_paise,
            collectible_amount_paise=gated.collectible_amount_paise,
            review_required_amount_paise=gated.review_required_amount_paise,
            not_collectible_amount_paise=gated.not_collectible_amount_paise,
            collectible_invoice_ids=collectible_ids,
            review_required_invoice_ids=list(gated.review_required_invoice_ids),
            not_collectible_invoice_ids=list(gated.not_collectible_invoice_ids),
            oldest_invoice_at=historical.oldest_invoice_at,
            newest_invoice_at=historical.newest_invoice_at,
            halted_at=episode.halted_at,
            reactivated_at=episode.reactivated_at,
            halt_duration_days=historical.halt_duration_days,
            card_type=subscription.card_type,
            risk_flags=risk_flags,
            historical_payment_success_rate=(
                customer.historical_payment_success_rate if customer else 0.75
            ),
            previous_failure_count=(
                customer.previous_failure_count if customer else 0
            ),
            previous_halt_count=customer.previous_halt_count if customer else 0,
            subscription_age_days=(
                customer.subscription_age_days if customer else 0
            ),
            customer_opted_out=(
                customer.customer_opted_out if customer else False
            ),
            has_active_dispute=(
                customer.has_active_dispute if customer else False
            ),
            policy_version=get_settings().policy_version,
            attempt_count=0,
            last_contact_at=None,
            created_at=now,
            updated_at=now,
        )
        assert draft.backlog_amount_paise == draft.collectible_amount_paise

        case, created = await self.cases.create_if_absent(draft)
        if not created:
            await self.trail.record(
                run_id=subscription.run_id,
                subscription_id=subscription.subscription_id,
                event_type=AuditEventType.RECOVERY_CASE_DUPLICATE,
                details={
                    "case_id": case.case_id,
                    "halt_episode_id": episode.episode_id,
                },
                actor=self.actor,
            )
            decision = (
                self._evaluate(subscription, customer, case)
                if case.is_strategy_eligible()
                else None
            )
            return RecoveryWindowResult(case, False, decision)

        await self.trail.record(
            run_id=subscription.run_id,
            subscription_id=subscription.subscription_id,
            event_type=AuditEventType.RECOVERY_CASE_CREATED,
            details={
                "case_id": case.case_id,
                "halt_episode_id": episode.episode_id,
                "status": case.status.value,
                "collectibility_status": case.collectibility_status.value,
                "invoice_count": case.invoice_count,
                "backlog_amount_paise": case.backlog_amount_paise,
                "collectible_amount_paise": case.collectible_amount_paise,
                "historical_unpaid_amount_paise": case.historical_unpaid_amount_paise,
                "review_required_amount_paise": case.review_required_amount_paise,
                "not_collectible_amount_paise": case.not_collectible_amount_paise,
            },
            actor=self.actor,
        )

        if not case.is_strategy_eligible():
            return RecoveryWindowResult(case, True, None)

        decision = self._evaluate(subscription, customer, case)
        await self.trail.record(
            run_id=subscription.run_id,
            subscription_id=subscription.subscription_id,
            event_type=AuditEventType.POLICY_EVALUATED,
            details={
                "case_id": case.case_id,
                "halt_episode_id": episode.episode_id,
                "policy_version": decision.policy_version,
                "allowed_actions": [a.value for a in decision.allowed_actions],
                "blocked_actions": [a.value for a in decision.blocked_actions],
                "reason_codes": [r.value for r in decision.reason_codes],
                "requires_escalation": decision.requires_escalation,
                "stop": decision.stop,
            },
            actor=self.actor,
        )

        if decision.requires_escalation:
            case = (
                await self.cases.update_status(
                    case.case_id, RecoveryCaseStatus.ESCALATED, utcnow()
                )
                or case
            )
            await self.trail.record(
                run_id=subscription.run_id,
                subscription_id=subscription.subscription_id,
                event_type=AuditEventType.RECOVERY_ESCALATED,
                details={
                    "case_id": case.case_id,
                    "reason_codes": [r.value for r in decision.reason_codes],
                },
                actor=self.actor,
            )

        return RecoveryWindowResult(case, True, decision)

    async def _persist_and_audit_collectibility(
        self,
        subscription: Subscription,
        halt_episode_id: str,
        gated: CollectibleBacklogResult,
    ) -> None:
        await self.trail.record(
            run_id=subscription.run_id,
            subscription_id=subscription.subscription_id,
            event_type=AuditEventType.COLLECTIBILITY_EVALUATED,
            details={
                "halt_episode_id": halt_episode_id,
                "historical_unpaid_amount_paise": gated.historical_unpaid_amount_paise,
                "collectible_amount_paise": gated.collectible_amount_paise,
                "not_collectible_amount_paise": gated.not_collectible_amount_paise,
                "review_required_amount_paise": gated.review_required_amount_paise,
                "collectible_invoice_ids": gated.collectible_invoice_ids,
                "not_collectible_invoice_ids": gated.not_collectible_invoice_ids,
                "review_required_invoice_ids": gated.review_required_invoice_ids,
                "reason_codes": [
                    code.value
                    for decision in gated.decisions
                    for code in decision.reason_codes
                ],
            },
            actor=self.actor,
        )
        for decision in gated.decisions:
            await self._audit_invoice_decision(subscription, halt_episode_id, decision)
            await self.backlog.invoices.set_collectibility(
                decision.invoice_id,
                status=decision.status,
                reason_codes=list(decision.reason_codes),
            )
        if gated.collectible_amount_paise > 0:
            await self.trail.record(
                run_id=subscription.run_id,
                subscription_id=subscription.subscription_id,
                event_type=AuditEventType.RECOVERABLE_BACKLOG_CONFIRMED,
                details={
                    "halt_episode_id": halt_episode_id,
                    "collectible_amount_paise": gated.collectible_amount_paise,
                    "collectible_invoice_ids": gated.collectible_invoice_ids,
                },
                actor=self.actor,
            )

    async def _audit_invoice_decision(
        self,
        subscription: Subscription,
        halt_episode_id: str,
        decision: CollectibilityDecision,
    ) -> None:
        await self.trail.record(
            run_id=subscription.run_id,
            subscription_id=subscription.subscription_id,
            event_type=_INVOICE_AUDIT[decision.status],
            details={
                "halt_episode_id": halt_episode_id,
                "invoice_id": decision.invoice_id,
                "collectibility_status": decision.status.value,
                "reason_codes": [c.value for c in decision.reason_codes],
                "eligible_amount_paise": decision.eligible_amount_paise,
            },
            actor=self.actor,
        )

    def _evaluate(self, subscription, customer, case: RecoveryCase) -> PolicyDecision:
        settings = get_settings()
        return evaluate_v1(
            PolicyContext(
                case_id=case.case_id,
                card_type=subscription.card_type,
                backlog_amount_paise=case.backlog_amount_paise,
                mandate_max_amount_paise=subscription.mandate_max_amount_paise,
                risk_flags=customer.risk_flags if customer else [],
                has_dispute=customer.has_active_dispute if customer else False,
                customer_opted_out=customer.customer_opted_out if customer else False,
                attempt_count=case.attempt_count,
                last_contact_at=case.last_contact_at,
                now=utcnow(),
                max_attempts=settings.policy_max_attempts,
                contact_cooldown_hours=settings.policy_contact_cooldown_hours,
            )
        )
