from fastapi import APIRouter, HTTPException, Query, status

from app.domain.time import utcnow
from app.models.documents import Customer, Subscription
from app.routes.deps import Audit, Customers, Events, Invoices, Subscriptions
from app.schemas.events import EventOut
from app.schemas.subscriptions import (
    AuditLogOut,
    CustomerIn,
    InvoiceOut,
    SubscriptionIn,
    SubscriptionOut,
)

router = APIRouter(prefix="/api", tags=["ledger"])


@router.post(
    "/customers", response_model=dict, status_code=status.HTTP_201_CREATED
)
async def create_customer(body: CustomerIn, customers: Customers):
    created = await customers.create(
        Customer(
            customer_id=body.customer_id,
            run_id=body.run_id,
            name=body.name,
            risk_flags=body.risk_flags,
            customer_opted_out=body.customer_opted_out,
            has_active_dispute=body.has_active_dispute,
            created_at=utcnow(),
        )
    )
    if not created:
        raise HTTPException(status.HTTP_409_CONFLICT, "customer_id already exists")
    return {"customer_id": body.customer_id, "created": True}


@router.post(
    "/subscriptions",
    response_model=SubscriptionOut,
    status_code=status.HTTP_201_CREATED,
)
async def create_subscription(
    body: SubscriptionIn, subscriptions: Subscriptions, customers: Customers
):
    if await customers.get(body.customer_id) is None:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND, f"unknown customer {body.customer_id}"
        )

    now = utcnow()
    created_at = body.created_at or now
    subscription = Subscription(
        subscription_id=body.subscription_id,
        run_id=body.run_id,
        customer_id=body.customer_id,
        status=body.status,
        plan_amount_paise=body.plan_amount_paise,
        currency=body.currency,
        card_type=body.card_type,
        mandate_max_amount_paise=body.mandate_max_amount_paise
        if body.mandate_max_amount_paise is not None
        else body.plan_amount_paise,
        halt_episodes=[],
        # Left unset: creation is not a state change, and seeding it from
        # `created_at` made every historical event look stale (INC-007).
        last_state_change_at=None,
        audit_seq=0,
        created_at=created_at,
        updated_at=now,
    )
    if not await subscriptions.create(subscription):
        raise HTTPException(status.HTTP_409_CONFLICT, "subscription_id already exists")
    return SubscriptionOut(**subscription.model_dump())


@router.get("/subscriptions/{subscription_id}", response_model=SubscriptionOut)
async def get_subscription(subscription_id: str, subscriptions: Subscriptions):
    subscription = await subscriptions.get(subscription_id)
    if subscription is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "unknown subscription")
    return SubscriptionOut(**subscription.model_dump())


@router.get("/subscriptions/{subscription_id}/events", response_model=list[EventOut])
async def list_subscription_events(subscription_id: str, events: Events):
    return [EventOut(**e.model_dump()) for e in await events.list_for_subscription(subscription_id)]


@router.get("/subscriptions/{subscription_id}/audit", response_model=list[AuditLogOut])
async def list_subscription_audit(subscription_id: str, audit: Audit):
    return [
        AuditLogOut(**a.model_dump())
        for a in await audit.list_for_subscription(subscription_id)
    ]


@router.get("/invoices", response_model=list[InvoiceOut])
async def list_invoices(
    invoices: Invoices,
    subscription_id: str = Query(description="Required in M1."),
):
    return [
        InvoiceOut(**i.model_dump())
        for i in await invoices.list_for_subscription(subscription_id)
    ]
