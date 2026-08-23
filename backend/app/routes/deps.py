from typing import Annotated

from fastapi import Depends
from pymongo.asynchronous.database import AsyncDatabase

from app.database import mongo
from app.repositories.audit import AuditRepository
from app.repositories.customers import CustomerRepository
from app.repositories.events import EventRepository
from app.repositories.invoices import InvoiceRepository
from app.repositories.subscriptions import SubscriptionRepository
from app.services.event_ingest import EventIngestService


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


def get_ingest_service(db: Db) -> EventIngestService:
    return EventIngestService(
        subscriptions=SubscriptionRepository(db),
        events=EventRepository(db),
        invoices=InvoiceRepository(db),
        audit=AuditRepository(db),
    )


Customers = Annotated[CustomerRepository, Depends(get_customers)]
Subscriptions = Annotated[SubscriptionRepository, Depends(get_subscriptions)]
Invoices = Annotated[InvoiceRepository, Depends(get_invoices)]
Events = Annotated[EventRepository, Depends(get_events)]
Audit = Annotated[AuditRepository, Depends(get_audit)]
Ingest = Annotated[EventIngestService, Depends(get_ingest_service)]
