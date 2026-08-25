"""Materialise a planned population through the real ledger path."""

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from app.domain.enums import (
    CardType,
    CollectibilityStatus,
    EventType,
    InvoiceStatus,
    RecoveryCaseStatus,
    ServiceDeliveryStatus,
    SubscriptionStatus,
)
from app.domain.time import to_storage_precision
from app.models.documents import Customer, Subscription
from app.repositories.customers import CustomerRepository
from app.repositories.recovery_cases import RecoveryCaseRepository
from app.repositories.subscriptions import SubscriptionRepository
from app.schemas.events import EventIn
from app.services.event_ingest import EventIngestService
from app.simulator.config import SimulationConfig
from app.simulator.identity import (
    halt_ordinal_from_episode_id,
    synthetic_case_key,
    synthetic_customer_key,
)
from app.simulator.population import Fate, SubscriberPlan, draw_population

ORIGIN = datetime(2024, 1, 1, 10, 0, tzinfo=UTC)
#: Frozen "now" so policy and recency scores do not depend on wall time.
DECISION_NOW = datetime(2026, 6, 1, 12, 0, tzinfo=UTC)

FIRST_NAMES = ("Priya", "Arjun", "Meera", "Rohit", "Ananya", "Kabir", "Isha", "Dev")


@dataclass(frozen=True)
class WorldSummary:
    subscriber_count: int
    always_active_count: int
    halted_never_returned_count: int
    reactivated_count: int
    recovery_case_count: int
    collectible_recovery_case_count: int
    review_required_case_count: int
    historical_invoice_count: int
    historical_unpaid_amount_paise: int
    collectible_amount_paise: int
    review_required_amount_paise: int
    not_collectible_amount_paise: int
    #: Collectible eligible receivable. Not raw historical invoices.
    revenue_at_risk_paise: int
    domestic_card_count: int
    international_card_count: int
    risk_case_count: int
    synthetic: bool = True


def _invoice_count(plans: list[SubscriberPlan]) -> int:
    first = sum(p.missed_cycles for p in plans if p.fate is not Fate.ALWAYS_ACTIVE)
    second = sum(
        max(1, p.missed_cycles // 2)
        for p in plans
        if p.fate is Fate.REACTIVATED and p.halt_cycles == 2
    )
    return first + second


def _at(base: datetime, **delta) -> datetime:
    return to_storage_precision(base + timedelta(**delta))


class WorldGenerator:
    def __init__(
        self,
        customers: CustomerRepository,
        subscriptions: SubscriptionRepository,
        ingest: EventIngestService,
    ) -> None:
        self.customers = customers
        self.subscriptions = subscriptions
        self.ingest = ingest

    async def generate(
        self, config: SimulationConfig, run_id: str
    ) -> tuple[list[SubscriberPlan], WorldSummary]:
        plans = draw_population(config)
        for plan in plans:
            await self._materialise(run_id, plan)
        await self._stamp_synthetic_identities(run_id)
        return plans, await self._summarise(run_id, plans)

    async def _materialise(self, run_id: str, plan: SubscriberPlan) -> None:
        customer_id = f"{run_id}_c{plan.index:04d}"
        subscription_id = f"{run_id}_s{plan.index:04d}"
        created = _at(ORIGIN, days=plan.index)
        name = f"{FIRST_NAMES[plan.index % len(FIRST_NAMES)]} {plan.index:04d}"

        await self.customers.create(
            Customer(
                customer_id=customer_id,
                run_id=run_id,
                synthetic_customer_key=synthetic_customer_key(plan.index),
                name=name,
                risk_flags=list(plan.risk_flags),
                customer_opted_out=plan.customer_opted_out,
                has_active_dispute=plan.has_active_dispute,
                historical_payment_success_rate=plan.historical_payment_success_rate,
                previous_failure_count=plan.previous_failure_count,
                previous_halt_count=plan.previous_halt_count,
                subscription_age_days=plan.subscription_age_days,
                created_at=created,
            )
        )
        await self.subscriptions.create(
            Subscription(
                subscription_id=subscription_id,
                run_id=run_id,
                customer_id=customer_id,
                status=SubscriptionStatus.ACTIVE,
                plan_amount_paise=plan.plan_amount_paise,
                card_type=plan.card_type,
                mandate_max_amount_paise=plan.plan_amount_paise,
                halt_episodes=[],
                last_state_change_at=None,
                created_at=created,
                updated_at=created,
            )
        )

        if plan.fate is Fate.ALWAYS_ACTIVE:
            return

        halt_start = _at(created, days=plan.halt_offset_days)
        await self._halt_cycle(
            run_id,
            subscription_id,
            tag="a",
            halt_at=halt_start,
            cycles=plan.missed_cycles,
            amount=plan.plan_amount_paise,
            reactivate=plan.fate is Fate.REACTIVATED,
            delivery=plan.first_halt_delivery,
        )
        if plan.fate is Fate.REACTIVATED and plan.halt_cycles == 2:
            second = _at(halt_start, days=30 * plan.missed_cycles + 50)
            await self._halt_cycle(
                run_id,
                subscription_id,
                tag="b",
                halt_at=second,
                cycles=max(1, plan.missed_cycles // 2),
                amount=plan.plan_amount_paise,
                reactivate=True,
                delivery=plan.second_halt_delivery,
            )

    async def _halt_cycle(
        self,
        run_id: str,
        subscription_id: str,
        *,
        tag: str,
        halt_at: datetime,
        cycles: int,
        amount: int,
        reactivate: bool,
        delivery: tuple[ServiceDeliveryStatus, ...] = (),
    ) -> None:
        pending_at = _at(halt_at, days=-5)
        await self.ingest.ingest(
            EventIn(
                event_id=f"{run_id}_{subscription_id}_{tag}_pending",
                event_type=EventType.SUBSCRIPTION_PENDING,
                subscription_id=subscription_id,
                occurred_at=pending_at,
                run_id=run_id,
            )
        )
        await self.ingest.ingest(
            EventIn(
                event_id=f"{run_id}_{subscription_id}_{tag}_halted",
                event_type=EventType.SUBSCRIPTION_HALTED,
                subscription_id=subscription_id,
                occurred_at=halt_at,
                run_id=run_id,
            )
        )
        for i in range(cycles):
            period = _at(halt_at, days=30 * i + 1)
            cycle = f"{period.year:04d}-{period.month:02d}"
            status = (
                delivery[i]
                if i < len(delivery)
                else ServiceDeliveryStatus.UNKNOWN
            )
            await self.ingest.ingest(
                EventIn(
                    event_id=f"{run_id}_{subscription_id}_{tag}_inv{i}",
                    event_type=EventType.INVOICE_CREATED,
                    subscription_id=subscription_id,
                    occurred_at=_at(period, days=8),
                    run_id=run_id,
                    payload={
                        "invoice_id": f"{run_id}_{subscription_id}_{tag}_inv{i}",
                        "billing_cycle": cycle,
                        "period_start": period.isoformat(),
                        "period_end": _at(period, days=30).isoformat(),
                        "amount_paise": amount,
                        "service_delivery_status": status.value,
                    },
                )
            )
        if reactivate:
            await self.ingest.ingest(
                EventIn(
                    event_id=f"{run_id}_{subscription_id}_{tag}_activated",
                    event_type=EventType.SUBSCRIPTION_ACTIVATED,
                    subscription_id=subscription_id,
                    occurred_at=_at(halt_at, days=30 * cycles + 12),
                    run_id=run_id,
                )
            )

    async def _stamp_synthetic_identities(self, run_id: str) -> None:
        """Write seed-stable keys onto cases created by the real recovery path."""
        cases = RecoveryCaseRepository(self.customers.db)
        for case in await cases.list_by_run(run_id):
            suffix = case.subscription_id.rsplit("_s", 1)[-1]
            index = int(suffix)
            ordinal = halt_ordinal_from_episode_id(case.halt_episode_id)
            await cases.set_synthetic_identity(
                case.case_id,
                synthetic_case_key=synthetic_case_key(index, ordinal),
                synthetic_customer_key=synthetic_customer_key(index),
            )

    async def _summarise(
        self, run_id: str, plans: list[SubscriberPlan]
    ) -> WorldSummary:
        cases = await RecoveryCaseRepository(self.customers.db).list_by_run(run_id)
        eligible = [c for c in cases if c.is_strategy_eligible()]
        review_cases = [c for c in cases if c.status is RecoveryCaseStatus.REVIEW_REQUIRED]
        invoices = await self.ingest.invoices.list_for_run(run_id)
        subscriptions = await self.subscriptions.list_for_run(run_id)
        closed_episodes = {
            episode.episode_id
            for sub in subscriptions
            for episode in sub.halt_episodes
            if episode.reactivated_at is not None
        }
        historical = 0
        collectible = 0
        review = 0
        excluded = 0
        for invoice in invoices:
            if invoice.halt_episode_id not in closed_episodes:
                continue
            if invoice.status is not InvoiceStatus.ISSUED_UNPAID:
                continue
            historical += int(invoice.amount_paise)
            status = invoice.collectibility_status
            if status is CollectibilityStatus.COLLECTIBLE:
                collectible += int(invoice.amount_paise)
            elif status is CollectibilityStatus.REVIEW_REQUIRED:
                review += int(invoice.amount_paise)
            else:
                excluded += int(invoice.amount_paise)
        at_risk = sum(c.collectible_amount_paise for c in eligible)
        assert at_risk == sum(c.backlog_amount_paise for c in eligible)
        return WorldSummary(
            subscriber_count=len(plans),
            always_active_count=sum(1 for p in plans if p.fate is Fate.ALWAYS_ACTIVE),
            halted_never_returned_count=sum(
                1 for p in plans if p.fate is Fate.HALTED_NEVER_RETURNED
            ),
            reactivated_count=sum(1 for p in plans if p.fate is Fate.REACTIVATED),
            recovery_case_count=len(cases),
            collectible_recovery_case_count=len(eligible),
            review_required_case_count=len(review_cases),
            historical_invoice_count=_invoice_count(plans),
            historical_unpaid_amount_paise=historical,
            collectible_amount_paise=collectible,
            review_required_amount_paise=review,
            not_collectible_amount_paise=excluded,
            revenue_at_risk_paise=at_risk,
            domestic_card_count=sum(1 for p in plans if p.card_type is CardType.DOMESTIC),
            international_card_count=sum(
                1 for p in plans if p.card_type is CardType.INTERNATIONAL
            ),
            risk_case_count=sum(1 for c in eligible if c.risk_flags),
        )
