"""Duplicate delivery protection (M1 tests 7-8)."""

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


def test_duplicate_event_id_does_not_repeat_the_transition(client):
    seed(client)
    first = send(client, "evt_same", "subscription.pending", at(hours=1))
    second = send(client, "evt_same", "subscription.pending", at(hours=1))

    assert first.json()["outcome"] == "processed"

    # A redelivery is normal for at-least-once webhooks, so it answers 200 and
    # tells the caller to stop retrying rather than raising an alert.
    assert second.status_code == 200
    assert second.json()["outcome"] == "duplicate"
    assert second.json()["reason_code"] == "DUPLICATE_EVENT"

    assert get_subscription(client)["status"] == "pending"

    audit = get_audit(client)
    transitions = [a for a in audit if a["event_type"] == "STATE_TRANSITION"]
    received = [a for a in audit if a["event_type"] == "EVENT_RECEIVED"]
    duplicates = [a for a in audit if a["event_type"] == "EVENT_DUPLICATE"]

    assert len(transitions) == 1, "the state transition must happen exactly once"
    assert len(received) == 1, "the event must be accepted exactly once"
    # The duplicate itself is recorded — a retry storm should be visible to an
    # auditor — but it repeats none of the original effects.
    assert len(duplicates) == 1


def test_duplicate_event_id_cannot_smuggle_a_different_payload(client):
    """Second delivery claiming a different state must still be a no-op."""
    seed(client)
    send(client, "evt_x", "subscription.pending", at(hours=1))
    r = send(client, "evt_x", "subscription.halted", at(hours=5))

    assert r.json()["outcome"] == "duplicate"
    assert get_subscription(client)["status"] == "pending"


def test_duplicate_invoice_event_does_not_create_a_second_invoice(client):
    seed(client)
    payload = invoice_payload("inv_1", "2026-02", months=1)

    first = send(client, "evt_inv", "invoice.created", at(days=31), payload)
    second = send(client, "evt_inv", "invoice.created", at(days=31), payload)

    assert first.json()["outcome"] == "processed"
    assert second.json()["outcome"] == "duplicate"
    assert len(get_invoices(client)) == 1


def test_same_invoice_under_a_new_event_id_is_refused(client):
    """Idempotency at the event layer cannot help here, so the unique index on
    invoice_id has to."""
    seed(client)
    payload = invoice_payload("inv_1", "2026-02", months=1)

    send(client, "evt_a", "invoice.created", at(days=31), payload)
    r = send(client, "evt_b", "invoice.created", at(days=31), payload)

    assert r.status_code == 409
    assert r.json()["reason_code"] == "DUPLICATE_INVOICE"
    assert len(get_invoices(client)) == 1


def test_billing_a_cycle_twice_is_refused(client):
    """Different invoice id, same subscription and cycle: the platform believes
    it is billing one period twice. The unique compound index stops it."""
    seed(client)
    send_invoice(
        client, "evt_a", "inv_1", "2026-02",
        months=1, occurred_at=at(days=31),
    )
    r = send(
        client,
        "evt_b",
        "invoice.created",
        at(days=32),
        invoice_payload("inv_2", "2026-02", months=1),
    )

    assert r.status_code == 409
    assert r.json()["reason_code"] == "DUPLICATE_BILLING_CYCLE"
    assert len(get_invoices(client)) == 1
