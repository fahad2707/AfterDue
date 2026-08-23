"""Late and out-of-order delivery (M1 test 10)."""

from tests.integration.helpers import at, get_audit, get_subscription, seed, send


def test_stale_lifecycle_event_is_rejected_without_corrupting_state(client):
    """`subscription.halted` happened at 10:00 but arrives after the 10:05
    activation. Receive order must not win over logical order."""
    seed(client)
    send(client, "e1", "subscription.pending", at(hours=1))
    send(client, "e2", "subscription.halted", at(hours=2))
    send(client, "e3", "subscription.activated", at(hours=3))

    before = get_subscription(client)

    late = send(client, "e_late", "subscription.pending", at(minutes=90))
    assert late.status_code == 409
    assert late.json()["reason_code"] == "STALE_EVENT"

    after = get_subscription(client)
    assert after["status"] == before["status"] == "active"
    assert after["halt_episodes"] == before["halt_episodes"]
    assert after["last_state_change_at"] == before["last_state_change_at"]


def test_stale_event_is_still_recorded_for_reconciliation(client):
    """Refusing to apply an event is not the same as pretending it never came."""
    seed(client)
    send(client, "e1", "subscription.pending", at(hours=1))
    send(client, "e2", "subscription.halted", at(hours=2))
    send(client, "e_late", "subscription.pending", at(minutes=30))

    events = client.get("/api/subscriptions/sub_priya/events").json()
    stale = next(e for e in events if e["event_id"] == "e_late")
    assert stale["processing_status"] == "rejected"
    assert stale["reason_code"] == "STALE_EVENT"

    rejected = [a for a in get_audit(client) if a["event_type"] == "EVENT_REJECTED"]
    assert len(rejected) == 1
    assert rejected[0]["details"]["reason_code"] == "STALE_EVENT"


def test_historical_event_into_a_freshly_created_subscription_is_accepted(client):
    """Regression for INC-007.

    A subscription created now, replaying a timeline from months ago, must
    work — that is exactly what M2's simulator does. Creation sets the state,
    it does not change it, so the first event has nothing to contradict.
    """
    client.post(
        "/api/customers",
        json={"customer_id": "cust_hist", "run_id": "run_test", "name": "Historic"},
    )
    r = client.post(
        "/api/subscriptions",
        json={
            "subscription_id": "sub_hist",
            "run_id": "run_test",
            "customer_id": "cust_hist",
            "plan_amount_paise": 499900,
            "card_type": "domestic",
        },
    )
    assert r.status_code == 201
    assert r.json()["last_state_change_at"] is None

    past = "2020-01-01T10:00:00+00:00"
    accepted = send(client, "e_old", "subscription.pending", past, subscription_id="sub_hist")
    assert accepted.status_code == 200, accepted.text
    assert accepted.json()["outcome"] == "processed"

    # The guard still applies once there is a transition to compare against.
    older = send(
        client,
        "e_older",
        "subscription.activated",
        "2019-06-01T10:00:00+00:00",
        subscription_id="sub_hist",
    )
    assert older.status_code == 409
    assert older.json()["reason_code"] == "STALE_EVENT"


def test_event_at_exactly_the_last_change_time_is_not_stale(client):
    """Strictly-older is stale; simultaneous is not, otherwise two events in the
    same millisecond would drop one arbitrarily."""
    seed(client)
    send(client, "e1", "subscription.pending", at(hours=1))
    r = send(client, "e2", "subscription.halted", at(hours=1))

    assert r.status_code == 200
    assert get_subscription(client)["status"] == "halted"
