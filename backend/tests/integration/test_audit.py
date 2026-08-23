"""Audit trail ordering and completeness (M1 test 11)."""

from datetime import UTC, datetime

from tests.integration.helpers import at, get_audit, seed, send, send_invoice


def test_audit_sequence_is_dense_and_ordered(client):
    seed(client)
    send(client, "e1", "subscription.pending", at(hours=1))
    send(client, "e2", "subscription.halted", at(hours=2))
    send_invoice(
        client, "i1", "inv_1", "2026-02",
        months=1, occurred_at=at(hours=3),
    )
    send(client, "e3", "subscription.activated", at(hours=4))

    audit = get_audit(client)
    seqs = [a["seq"] for a in audit]

    assert seqs == sorted(seqs), "must be returned in sequence order"
    assert seqs == list(range(1, len(seqs) + 1)), "no gaps, no duplicates"


def test_audit_ordering_survives_identical_timestamps(client, monkeypatch):
    """Ordering must come from `seq`, never from `ts`.

    The clock is frozen so every entry lands on the same millisecond. Relying
    on real latency to produce a collision would make this test a measurement
    of Atlas round-trip time rather than of the invariant.
    """
    import app.services.audit as audit_module

    frozen = datetime(2026, 1, 1, 10, 0, 0, tzinfo=UTC)
    monkeypatch.setattr(audit_module, "utcnow", lambda: frozen)

    seed(client)
    send(client, "e1", "subscription.pending", at(hours=1))
    send(client, "e2", "subscription.halted", at(hours=2))

    audit = get_audit(client)
    assert len(audit) > 2

    timestamps = {a["ts"] for a in audit}
    assert len(timestamps) == 1, "clock should be frozen for this test"

    seqs = [a["seq"] for a in audit]
    assert len(set(seqs)) == len(seqs), "colliding timestamps still need unique seqs"
    assert seqs == list(range(1, len(seqs) + 1))


def test_halt_cycle_records_the_expected_audit_events(client):
    seed(client)
    send(client, "e1", "subscription.pending", at(hours=1))
    send(client, "e2", "subscription.halted", at(hours=2))
    send_invoice(
        client, "i1", "inv_1", "2026-02",
        months=1, occurred_at=at(hours=3),
    )
    send(client, "e3", "subscription.activated", at(hours=4))

    kinds = [a["event_type"] for a in get_audit(client)]

    assert kinds.count("HALT_EPISODE_OPENED") == 1
    assert kinds.count("HALT_EPISODE_CLOSED") == 1
    assert kinds.count("INVOICE_RECORDED") == 1
    assert kinds.count("STATE_TRANSITION") == 3
    assert kinds.count("EVENT_RECEIVED") == 4
    assert kinds.count("EVENT_PROCESSED") == 4

    assert kinds.index("HALT_EPISODE_OPENED") < kinds.index("INVOICE_RECORDED")
    assert kinds.index("INVOICE_RECORDED") < kinds.index("HALT_EPISODE_CLOSED")


def test_closing_audit_entry_reports_the_invoices_stranded_by_the_halt(client):
    seed(client)
    send(client, "e1", "subscription.pending", at(hours=1))
    send(client, "e2", "subscription.halted", at(hours=2))
    send_invoice(
        client, "i1", "inv_1", "2026-02",
        months=1, occurred_at=at(hours=3),
    )
    send_invoice(
        client, "i2", "inv_2", "2026-03",
        months=2, occurred_at=at(hours=4),
    )
    send(client, "e3", "subscription.activated", at(hours=5))

    closed = next(a for a in get_audit(client) if a["event_type"] == "HALT_EPISODE_CLOSED")
    assert closed["details"]["episode_id"] == "he_1"
    assert closed["details"]["invoice_count"] == 2
