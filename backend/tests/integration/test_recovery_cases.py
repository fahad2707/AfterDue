"""Recovery-case creation, idempotency, and reconciliation (M2 tests 21-29)."""

from pymongo import MongoClient
from pymongo.errors import DuplicateKeyError

from tests.integration.helpers import (
    CUSTOMER_ID,
    PLAN_PAISE,
    RUN_ID,
    SUBSCRIPTION_ID,
    at,
    get_audit,
    seed,
    send,
    send_invoice,
)


def halt_with_invoices(client, n: int = 2, subscription_id: str = SUBSCRIPTION_ID):
    send(client, "e1", "subscription.pending", at(hours=1), subscription_id=subscription_id)
    send(client, "e2", "subscription.halted", at(hours=2), subscription_id=subscription_id)
    months = ["2026-02", "2026-03", "2026-04"]
    for i in range(n):
        send_invoice(
            client,
            f"i{i+1}",
            f"inv_{i+1}",
            months[i],
            months=i + 1,
            occurred_at=at(hours=3 + i),
            subscription_id=subscription_id,
        )


def test_halted_to_active_with_backlog_creates_one_case(client):
    seed(client)
    halt_with_invoices(client, n=2)
    r = send(client, "e3", "subscription.activated", at(hours=10))
    assert r.status_code == 200, r.text

    listed = client.get("/api/recovery-cases", params={"run_id": RUN_ID})
    assert listed.status_code == 200
    cases = listed.json()
    assert len(cases) == 1
    case = cases[0]
    assert case["subscription_id"] == SUBSCRIPTION_ID
    assert case["customer_id"] == CUSTOMER_ID
    assert case["halt_episode_id"] == "he_1"
    assert case["run_id"] == RUN_ID
    assert case["invoice_count"] == 2
    assert case["backlog_amount_paise"] == 2 * PLAN_PAISE
    assert isinstance(case["backlog_amount_paise"], int)


def test_pending_to_active_creates_no_case(client):
    seed(client)
    send(client, "e1", "subscription.pending", at(hours=1))
    send(client, "e2", "subscription.activated", at(hours=2))
    cases = client.get("/api/recovery-cases", params={"run_id": RUN_ID}).json()
    assert cases == []


def test_zero_backlog_produces_no_recovery_case(client):
    seed(client)
    send(client, "e1", "subscription.pending", at(hours=1))
    send(client, "e2", "subscription.halted", at(hours=2))
    send(client, "e3", "subscription.activated", at(hours=3))
    cases = client.get("/api/recovery-cases", params={"run_id": RUN_ID}).json()
    assert cases == []
    kinds = [a["event_type"] for a in get_audit(client)]
    assert "NO_BACKLOG_FOUND" in kinds
    assert "RECOVERY_CASE_CREATED" not in kinds


def test_paid_invoice_before_activation_is_excluded_from_case(client):
    seed(client)
    send(client, "e1", "subscription.pending", at(hours=1))
    send(client, "e2", "subscription.halted", at(hours=2))
    send_invoice(client, "i1", "inv_1", "2026-02", months=1, occurred_at=at(hours=3))
    send_invoice(client, "i2", "inv_2", "2026-03", months=2, occurred_at=at(hours=4))
    send(client, "p1", "payment.succeeded", at(hours=5), {"invoice_id": "inv_1"})
    send(client, "e3", "subscription.activated", at(hours=6))

    cases = client.get("/api/recovery-cases", params={"run_id": RUN_ID}).json()
    assert len(cases) == 1
    assert cases[0]["invoice_ids"] == ["inv_2"]
    assert cases[0]["backlog_amount_paise"] == PLAN_PAISE


def test_duplicate_activation_cannot_create_second_case(client):
    seed(client)
    halt_with_invoices(client, n=1)
    send(client, "e3", "subscription.activated", at(hours=10))
    replay = send(client, "e3", "subscription.activated", at(hours=10))
    assert replay.json()["outcome"] == "duplicate"
    noop = send(client, "e4", "subscription.activated", at(hours=11))
    assert noop.json()["reason_code"] == "NO_OP_SAME_STATE"
    cases = client.get("/api/recovery-cases", params={"run_id": RUN_ID}).json()
    assert len(cases) == 1


def test_repeat_halt_episodes_create_separate_recovery_cases(client):
    seed(client)
    send(client, "e1", "subscription.pending", at(hours=1))
    send(client, "e2", "subscription.halted", at(hours=2))
    send_invoice(client, "i1", "inv_1", "2026-02", months=1, occurred_at=at(hours=3))
    send(client, "e3", "subscription.activated", at(hours=4))

    send(client, "e4", "subscription.pending", at(hours=5))
    send(client, "e5", "subscription.halted", at(hours=6))
    send_invoice(client, "i2", "inv_2", "2026-03", months=2, occurred_at=at(hours=7))
    send(client, "e6", "subscription.activated", at(hours=8))

    cases = client.get("/api/recovery-cases", params={"run_id": RUN_ID}).json()
    assert {c["halt_episode_id"] for c in cases} == {"he_1", "he_2"}
    assert all(c["run_id"] == RUN_ID for c in cases)
    assert all(c["customer_id"] == CUSTOMER_ID for c in cases)


def test_unique_index_rejects_second_case_for_same_episode(
    client, mongo_uri, test_db_name
):
    seed(client)
    halt_with_invoices(client, n=1)
    send(client, "e3", "subscription.activated", at(hours=10))
    db = MongoClient(mongo_uri)[test_db_name]
    existing = db.recovery_cases.find_one({"subscription_id": SUBSCRIPTION_ID})
    assert existing is not None
    clone = {k: v for k, v in existing.items() if k != "_id"}
    clone["case_id"] = "case_should_not_land"
    try:
        db.recovery_cases.insert_one(clone)
        raise AssertionError("unique index should have rejected the second case")
    except DuplicateKeyError:
        pass
    assert db.recovery_cases.count_documents({"subscription_id": SUBSCRIPTION_ID}) == 1


def test_reconciliation_rebuilds_a_lost_case(client, monkeypatch):
    """Activation must succeed even when recovery-case creation is lost."""
    from app.services import event_ingest as ingest_mod

    seed(client)
    halt_with_invoices(client, n=2)

    async def boom(*_args, **_kwargs):
        raise RuntimeError("simulated crash after transition")

    with monkeypatch.context() as patched:
        patched.setattr(
            ingest_mod.RecoveryWindowService, "handle_reactivation", boom
        )
        activated = send(client, "e3", "subscription.activated", at(hours=10))
    assert activated.status_code == 200
    assert activated.json()["outcome"] == "processed"
    assert activated.json()["subscription"]["status"] == "active"
    assert client.get("/api/recovery-cases", params={"run_id": RUN_ID}).json() == []

    report = client.post("/api/recovery-cases/reconcile")
    assert report.status_code == 200, report.text
    body = report.json()
    assert len(body["created_case_ids"]) == 1

    cases = client.get("/api/recovery-cases", params={"run_id": RUN_ID}).json()
    assert len(cases) == 1
    assert cases[0]["invoice_count"] == 2


def test_reconciliation_is_idempotent(client):
    seed(client)
    halt_with_invoices(client, n=1)
    send(client, "e3", "subscription.activated", at(hours=10))
    first = client.post("/api/recovery-cases/reconcile").json()
    second = client.post("/api/recovery-cases/reconcile").json()
    assert first["created_case_ids"] == []
    assert second["created_case_ids"] == []
    assert second["already_present"] >= 1
    assert len(client.get("/api/recovery-cases", params={"run_id": RUN_ID}).json()) == 1
