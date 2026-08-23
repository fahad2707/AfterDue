"""Invoice attribution to halt episodes (M1 tests 5-6, 12)."""

from tests.integration.helpers import (
    at,
    get_invoices,
    get_subscription,
    invoice_payload,
    seed,
    send,
    send_invoice,
)


def halt(client):
    send(client, "h1", "subscription.pending", at(hours=1))
    send(client, "h2", "subscription.halted", at(hours=2))


def test_invoice_created_during_halt_is_linked_to_the_episode(client):
    seed(client)
    halt(client)

    send_invoice(
        client, "i1", "inv_1", "2026-02",
        months=1, occurred_at=at(days=31),
    )

    invoice = get_invoices(client)[0]
    assert invoice["halt_episode_id"] == "he_1"
    assert invoice["generated_during_halt"] is True

    episode = get_subscription(client)["halt_episodes"][0]
    assert episode["invoice_ids"] == ["inv_1"]


def test_invoice_created_while_active_has_no_episode(client):
    seed(client)
    send_invoice(
        client, "i1", "inv_1", "2026-02",
        months=1, occurred_at=at(days=31),
    )

    invoice = get_invoices(client)[0]
    assert invoice["halt_episode_id"] is None
    assert invoice["generated_during_halt"] is False
    assert get_subscription(client)["halt_episodes"] == []


def test_invoices_are_attributed_to_the_episode_that_contains_them(client):
    """Two separate halts, one invoice each: lineage must not collapse."""
    seed(client)
    send(client, "e1", "subscription.pending", at(hours=1))
    send(client, "e2", "subscription.halted", at(hours=2))
    send_invoice(
        client, "i1", "inv_1", "2026-02",
        months=1, occurred_at=at(hours=3),
    )
    send(client, "e3", "subscription.activated", at(hours=4))

    # Between halts: this one belongs to no episode.
    send_invoice(
        client, "i2", "inv_2", "2026-03",
        months=2, occurred_at=at(hours=5),
    )

    send(client, "e4", "subscription.pending", at(hours=6))
    send(client, "e5", "subscription.halted", at(hours=7))
    send_invoice(
        client, "i3", "inv_3", "2026-04",
        months=3, occurred_at=at(hours=8),
    )

    by_id = {i["invoice_id"]: i for i in get_invoices(client)}
    assert by_id["inv_1"]["halt_episode_id"] == "he_1"
    assert by_id["inv_2"]["halt_episode_id"] is None
    assert by_id["inv_3"]["halt_episode_id"] == "he_2"

    episodes = {e["episode_id"]: e for e in get_subscription(client)["halt_episodes"]}
    assert episodes["he_1"]["invoice_ids"] == ["inv_1"]
    assert episodes["he_2"]["invoice_ids"] == ["inv_3"]


def test_late_invoice_is_attributed_by_when_it_happened_not_when_it_arrived(client):
    """An invoice raised during the halt but delivered after reactivation still
    belongs to that halt — this is the lineage M2's backlog depends on."""
    seed(client)
    send(client, "e1", "subscription.pending", at(hours=1))
    send(client, "e2", "subscription.halted", at(hours=2))
    send(client, "e3", "subscription.activated", at(hours=6))

    # occurred_at falls inside the closed episode window.
    send_invoice(
        client, "i_late", "inv_late", "2026-02",
        months=1, occurred_at=at(hours=4),
    )

    invoice = get_invoices(client)[0]
    assert invoice["halt_episode_id"] == "he_1"
    assert invoice["generated_during_halt"] is True
    assert get_subscription(client)["halt_episodes"][0]["invoice_ids"] == ["inv_late"]


def test_amounts_stay_integer_paise_end_to_end(client):
    seed(client)
    send_invoice(
        client, "i1", "inv_1", "2026-02",
        months=1, occurred_at=at(days=31),
    )

    invoice = get_invoices(client)[0]
    assert isinstance(invoice["amount_paise"], int)
    assert invoice["amount_paise"] == 499900
    assert invoice["amount_display"] == "₹4,999.00"


def test_float_amount_is_refused_at_the_api_boundary(client):
    seed(client)
    payload = invoice_payload("inv_1", "2026-02", months=1)
    payload["amount_paise"] = 4999.5

    r = send(client, "i1", "invoice.created", at(days=31), payload)
    assert r.status_code in (409, 422)
    assert get_invoices(client) == []
