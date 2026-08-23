"""The full M1 ledger walk: ACTIVE -> PENDING -> HALTED -> 2 invoices -> ACTIVE.

This is the timeline RECLAIM exists for. M1 stops at reconstructing it
faithfully; deciding what to do about the stranded invoices is M2 onward.
"""

from tests.integration.helpers import (
    at,
    get_audit,
    get_invoices,
    get_subscription,
    invoice_payload,
    seed,
    send,
    send_invoice,
)


def test_full_halt_cycle_produces_a_coherent_ledger(client):
    seed(client)

    steps = [
        ("e1", "subscription.pending", at(hours=1), None),
        ("e2", "subscription.halted", at(hours=2), None),
        ("i1", "invoice.created", at(days=31), invoice_payload("inv_feb", "2026-02", months=1)),
        ("i2", "invoice.created", at(days=61), invoice_payload("inv_mar", "2026-03", months=2)),
        ("e3", "subscription.activated", at(days=70), None),
    ]
    for event_id, event_type, occurred_at, payload in steps:
        r = send(client, event_id, event_type, occurred_at, payload)
        assert r.status_code == 200, f"{event_id}: {r.text}"
        assert r.json()["outcome"] == "processed", f"{event_id}: {r.json()}"

    sub = get_subscription(client)
    assert sub["status"] == "active"

    assert len(sub["halt_episodes"]) == 1
    episode = sub["halt_episodes"][0]
    assert episode["halted_at"] is not None
    assert episode["reactivated_at"] is not None
    assert episode["invoice_ids"] == ["inv_feb", "inv_mar"]

    invoices = get_invoices(client)
    assert len(invoices) == 2
    assert all(i["halt_episode_id"] == "he_1" for i in invoices)
    assert all(i["generated_during_halt"] for i in invoices)
    assert all(i["status"] == "issued_unpaid" for i in invoices)

    # The stranded backlog M2 will reconstruct: 2 x ₹4,999.00.
    backlog = sum(i["amount_paise"] for i in invoices)
    assert backlog == 999800
    assert all(isinstance(i["amount_paise"], int) for i in invoices)

    audit = get_audit(client)
    assert [a["seq"] for a in audit] == list(range(1, len(audit) + 1))

    kinds = [a["event_type"] for a in audit]
    assert kinds.count("STATE_TRANSITION") == 3
    assert kinds.count("HALT_EPISODE_OPENED") == 1
    assert kinds.count("HALT_EPISODE_CLOSED") == 1
    assert kinds.count("INVOICE_RECORDED") == 2

    events = client.get("/api/subscriptions/sub_priya/events").json()
    assert len(events) == 5
    assert all(e["processing_status"] == "processed" for e in events)
    # occurred_at and received_at are genuinely different clocks.
    assert all(e["occurred_at"] != e["received_at"] for e in events)


def test_payment_succeeded_settles_an_invoice_without_moving_subscription_state(client):
    seed(client)
    send(client, "e1", "subscription.pending", at(hours=1))
    send(client, "e2", "subscription.halted", at(hours=2))
    send_invoice(
        client, "i1", "inv_feb", "2026-02",
        months=1, occurred_at=at(hours=3),
    )

    r = send(client, "p1", "payment.succeeded", at(hours=4), {"invoice_id": "inv_feb"})
    assert r.status_code == 200
    assert r.json()["outcome"] == "processed"

    assert get_invoices(client)[0]["status"] == "paid"
    # Only the platform's lifecycle events move subscription status.
    assert get_subscription(client)["status"] == "halted"
    assert "INVOICE_PAID" in [a["event_type"] for a in get_audit(client)]


def test_event_for_unknown_subscription_is_refused(client):
    r = send(client, "e1", "subscription.pending", at(hours=1), subscription_id="sub_nope")
    assert r.status_code == 404
