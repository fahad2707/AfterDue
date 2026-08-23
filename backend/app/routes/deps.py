from typing import Annotated

from fastapi import Depends
from pymongo.asynchronous.database import AsyncDatabase

from app.database import mongo
from app.repositories.audit import AuditRepository
from app.repositories.customers import CustomerRepository
from app.repositories.events import EventRepository
from app.repositories.invoices import InvoiceRepository
from app.repositories.recovery_cases import RecoveryCaseRepository
from app.repositories.subscriptions import SubscriptionRepository
from app.services.audit import AuditTrail
from app.services.backlog_builder import BacklogBuilder
from app.services.event_ingest import EventIngestService
from app.services.reconciliation import ReconciliationService
from app.services.recovery_window import RecoveryWindowService


def get_db() -> AsyncDatabase:
    return mongo.db


Db = Annotated[AsyncDatabase, Depends(get_db)]


def get_customers(db: Db) -> CustomerRepository:
    return CustomerRepository(db)


def get_subscriptions(db: Db) -> SubscriptionRepository:
    return SubscriptionRepository(db)


def get_invoices(db: Db) -> InvoiceRepository:
    return InvoiceRepository(db)


def get_events(db: Db) -> EventRepository:
    return EventRepository(db)


def get_audit(db: Db) -> AuditRepository:
    return AuditRepository(db)


def get_cases(db: Db) -> RecoveryCaseRepository:
    return RecoveryCaseRepository(db)


def get_ingest_service(db: Db) -> EventIngestService:
    subscriptions = SubscriptionRepository(db)
    invoices = InvoiceRepository(db)
    customers = CustomerRepository(db)
    cases = RecoveryCaseRepository(db)
    audit = AuditRepository(db)
    trail = AuditTrail(subscriptions, audit)
    recovery = RecoveryWindowService(
        customers=customers,
        cases=cases,
        backlog=BacklogBuilder(invoices),
        trail=trail,
    )
    return EventIngestService(
        subscriptions=subscriptions,
        events=EventRepository(db),
        invoices=invoices,
        audit=audit,
        recovery=recovery,
    )


def get_reconcile(db: Db) -> ReconciliationService:
    subscriptions = SubscriptionRepository(db)
    return ReconciliationService(
        subscriptions=subscriptions,
        invoices=InvoiceRepository(db),
        customers=CustomerRepository(db),
        cases=RecoveryCaseRepository(db),
        trail=AuditTrail(subscriptions, AuditRepository(db)),
    )


Customers = Annotated[CustomerRepository, Depends(get_customers)]
Subscriptions = Annotated[SubscriptionRepository, Depends(get_subscriptions)]
Invoices = Annotated[InvoiceRepository, Depends(get_invoices)]
Events = Annotated[EventRepository, Depends(get_events)]
Audit = Annotated[AuditRepository, Depends(get_audit)]
Cases = Annotated[RecoveryCaseRepository, Depends(get_cases)]
Ingest = Annotated[EventIngestService, Depends(get_ingest_service)]
Reconcile = Annotated[ReconciliationService, Depends(get_reconcile)]
