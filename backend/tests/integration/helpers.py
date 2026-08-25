from datetime import UTC, datetime, timedelta

RUN_ID = "run_test"
CUSTOMER_ID = "cust_priya"
SUBSCRIPTION_ID = "sub_priya"
PLAN_PAISE = 499900  # ₹4,999.00

#: Fixed base time so every test reads as a deterministic timeline.
T0 = datetime(2026, 1, 1, 10, 0, 0, tzinfo=UTC)


def at(**offset) -> str:
    return (T0 + timedelta(**offset)).isoformat()


def seed(
    client,
    *,
    status: str = "active",
    subscription_id: str = SUBSCRIPTION_ID,
    customer_id: str = CUSTOMER_ID,
    run_id: str = RUN_ID,
    card_type: str = "domestic",
    name: str = "Priya Sharma",
    risk_flags: list[str] | None = None,
    customer_opted_out: bool = False,
    has_active_dispute: bool = False,
    mandate_max_amount_paise: int | None = None,
):
    client.post(
        "/api/customers",
        json={
            "customer_id": customer_id,
            "run_id": run_id,
            "name": name,
            "risk_flags": risk_flags or [],
            "customer_opted_out": customer_opted_out,
            "has_active_dispute": has_active_dispute,
        },
    )
    body = {
        "subscription_id": subscription_id,
        "run_id": run_id,
        "customer_id": customer_id,
        "plan_amount_paise": PLAN_PAISE,
        "card_type": card_type,
        "status": status,
        "created_at": T0.isoformat(),
    }
    if mandate_max_amount_paise is not None:
        body["mandate_max_amount_paise"] = mandate_max_amount_paise
    r = client.post("/api/subscriptions", json=body)
    assert r.status_code == 201, r.text
    return r.json()


def send(
    client,
    event_id: str,
    event_type: str,
    occurred_at: str,
    payload: dict | None = None,
    subscription_id: str = SUBSCRIPTION_ID,
):
    return client.post(
        "/api/events",
        json={
            "event_id": event_id,
            "event_type": event_type,
            "subscription_id": subscription_id,
            "occurred_at": occurred_at,
            "payload": payload or {},
        },
    )


def send_invoice(
    client,
    event_id: str,
    invoice_id: str,
    cycle: str,
    *,
    months: int,
    occurred_at: str,
    amount: int = PLAN_PAISE,
    subscription_id: str = SUBSCRIPTION_ID,
    service_delivery_status: str = "delivered",
):
    return send(
        client,
        event_id,
        "invoice.created",
        occurred_at,
        invoice_payload(
            invoice_id,
            cycle,
            months=months,
            amount=amount,
            service_delivery_status=service_delivery_status,
        ),
        subscription_id=subscription_id,
    )


def invoice_payload(
    invoice_id: str,
    cycle: str,
    *,
    months: int,
    amount: int = PLAN_PAISE,
    service_delivery_status: str | None = "delivered",
):
    """Test helper. Default DELIVERED so existing recovery tests stay collectible.

    Omit `service_delivery_status` (pass None) to exercise ingest fail-closed
    UNKNOWN. The engine itself still defaults missing delivery to UNKNOWN.
    """
    start = T0 + timedelta(days=30 * months)
    payload = {
        "invoice_id": invoice_id,
        "billing_cycle": cycle,
        "period_start": start.isoformat(),
        "period_end": (start + timedelta(days=30)).isoformat(),
        "amount_paise": amount,
    }
    if service_delivery_status is not None:
        payload["service_delivery_status"] = service_delivery_status
    return payload


def get_subscription(client, subscription_id: str = SUBSCRIPTION_ID):
    r = client.get(f"/api/subscriptions/{subscription_id}")
    assert r.status_code == 200, r.text
    return r.json()


def get_audit(client, subscription_id: str = SUBSCRIPTION_ID):
    r = client.get(f"/api/subscriptions/{subscription_id}/audit")
    assert r.status_code == 200, r.text
    return r.json()


def get_invoices(client, subscription_id: str = SUBSCRIPTION_ID):
    r = client.get("/api/invoices", params={"subscription_id": subscription_id})
    assert r.status_code == 200, r.text
    return r.json()
