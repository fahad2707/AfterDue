"""Subscription lifecycle transitions and halt episodes (M1 tests 1-4, 9)."""

from tests.integration.helpers import at, get_audit, get_subscription, seed, send


def test_active_to_pending(client):
    seed(client)
    r = send(client, "evt_1", "subscription.pending", at(hours=1))
    assert r.status_code == 200, r.text
    assert r.json()["outcome"] == "processed"
    assert get_subscription(client)["status"] == "pending"


def test_pending_to_halted_opens_one_episode(client):
    seed(client)
    send(client, "evt_1", "subscription.pending", at(hours=1))
    r = send(client, "evt_2", "subscription.halted", at(hours=2))
    assert r.status_code == 200, r.text

    sub = get_subscription(client)
    assert sub["status"] == "halted"
    assert len(sub["halt_episodes"]) == 1

    episode = sub["halt_episodes"][0]
    assert episode["episode_id"] == "he_1"
    assert episode["reactivated_at"] is None
    assert episode["invoice_ids"] == []


def test_halted_to_active_closes_the_episode(client):
    seed(client)
    send(client, "evt_1", "subscription.pending", at(hours=1))
    send(client, "evt_2", "subscription.halted", at(hours=2))
    r = send(client, "evt_3", "subscription.activated", at(hours=3))
    assert r.status_code == 200, r.text

    sub = get_subscription(client)
    assert sub["status"] == "active"
    assert len(sub["halt_episodes"]) == 1
    assert sub["halt_episodes"][0]["reactivated_at"] is not None


def test_second_halt_creates_a_second_episode_without_touching_the_first(client):
    """The defect the scalar halted_at/reactivated_at design would have caused."""
    seed(client)
    send(client, "e1", "subscription.pending", at(hours=1))
    send(client, "e2", "subscription.halted", at(hours=2))
    send(client, "e3", "subscription.activated", at(hours=3))
    send(client, "e4", "subscription.pending", at(hours=4))
    send(client, "e5", "subscription.halted", at(hours=5))

    sub = get_subscription(client)
    assert sub["status"] == "halted"
    assert [e["episode_id"] for e in sub["halt_episodes"]] == ["he_1", "he_2"]

    first, second = sub["halt_episodes"]
    assert first["reactivated_at"] is not None, "first episode must stay closed"
    assert second["reactivated_at"] is None, "second episode must be open"
    assert first["halted_at"] != second["halted_at"]

    send(client, "e6", "subscription.activated", at(hours=6))
    sub = get_subscription(client)
    assert all(e["reactivated_at"] is not None for e in sub["halt_episodes"])
    assert len(sub["halt_episodes"]) == 2


def test_illegal_transition_is_rejected_and_state_is_unchanged(client):
    """ACTIVE -> HALTED must pass through PENDING."""
    seed(client)
    r = send(client, "evt_bad", "subscription.halted", at(hours=1))

    assert r.status_code == 409
    body = r.json()
    assert body["outcome"] == "rejected"
    assert body["reason_code"] == "ILLEGAL_TRANSITION"

    sub = get_subscription(client)
    assert sub["status"] == "active"
    assert sub["halt_episodes"] == []

    kinds = [a["event_type"] for a in get_audit(client)]
    assert "STATE_TRANSITION" not in kinds
    assert "EVENT_REJECTED" in kinds


def test_redelivered_state_is_a_no_op_not_an_error(client):
    seed(client)
    send(client, "e1", "subscription.pending", at(hours=1))
    r = send(client, "e2_distinct_id", "subscription.pending", at(hours=2))

    assert r.status_code == 200
    assert r.json()["reason_code"] == "NO_OP_SAME_STATE"
    assert get_subscription(client)["status"] == "pending"

    transitions = [a for a in get_audit(client) if a["event_type"] == "STATE_TRANSITION"]
    assert len(transitions) == 1
