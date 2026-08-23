from datetime import UTC, datetime, timedelta

RUN_ID = "run_test"
CUSTOMER_ID = "cust_priya"
SUBSCRIPTION_ID = "sub_priya"
PLAN_PAISE = 499900  # ₹4,999.00

#: Fixed base time so every test reads as a deterministic timeline.
T0 = datetime(2026, 1, 1, 10, 0, 0, tzinfo=UTC)


def at(**offset) -> str:
    return (T0 + timedelta(**offset)).isoformat()


def seed(client, *, status: str = "active", subscription_id: str = SUBSCRIPTION_ID):
    client.post(
        "/api/customers",
        json={"customer_id": CUSTOMER_ID, "run_id": RUN_ID, "name": "Priya Sharma"},
    )
    r = client.post(
        "/api/subscriptions",
        json={
            "subscription_id": subscription_id,
            "run_id": RUN_ID,
            "customer_id": CUSTOMER_ID,
            "plan_amount_paise": PLAN_PAISE,
            "card_type": "domestic",
            "status": status,
            "created_at": T0.isoformat(),
        },
    )
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
):
    return send(
        client,
        event_id,
        "invoice.created",
        occurred_at,
        invoice_payload(invoice_id, cycle, months=months, amount=amount),
    )


def invoice_payload(invoice_id: str, cycle: str, *, months: int, amount: int = PLAN_PAISE):
    start = T0 + timedelta(days=30 * months)
    return {
        "invoice_id": invoice_id,
        "billing_cycle": cycle,
        "period_start": start.isoformat(),
        "period_end": (start + timedelta(days=30)).isoformat(),
        "amount_paise": amount,
    }


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
