"""M7 adversarial integration: ingest, policy mutation, artifacts, money."""

from concurrent.futures import ThreadPoolExecutor

from pymongo import MongoClient

from tests.integration.helpers import (
    PLAN_PAISE,
    at,
    invoice_payload,
    seed,
    send,
    send_invoice,
)
from tests.integration.test_m6_agent import _open_case


def test_wrong_run_id_is_rejected(client):
    seed(client)
    res = client.post(
        "/api/events",
        json={
            "event_id": "evt_wrong_run",
            "event_type": "subscription.pending",
            "subscription_id": "sub_priya",
            "occurred_at": at(hours=1),
            "run_id": "run_other",
        },
    )
    assert res.status_code == 409
    assert res.json()["reason_code"] == "RUN_ID_MISMATCH"
    assert client.get("/api/subscriptions/sub_priya").json()["status"] == "active"


def test_malformed_invoice_payload_is_rejected(client):
    seed(client)
    send(client, "e1", "subscription.pending", at(hours=1))
    send(client, "e2", "subscription.halted", at(hours=2))
    res = send(
        client,
        "inv_bad",
        "invoice.created",
        at(hours=3),
        {"invoice_id": "inv_x"},
    )
    assert res.status_code == 422
    assert res.json()["reason_code"] == "MALFORMED_PAYLOAD"
    invoices = client.get("/api/invoices", params={"subscription_id": "sub_priya"}).json()
    assert invoices == []


def test_payment_on_missing_invoice_is_rejected(client):
    seed(client)
    res = send(
        client,
        "pay_missing",
        "payment.succeeded",
        at(hours=1),
        {"invoice_id": "inv_does_not_exist", "amount_paise": PLAN_PAISE},
    )
    assert res.status_code == 422
    assert res.json()["reason_code"] == "INVOICE_NOT_FOUND"


def test_concurrent_pending_only_one_transition_wins(client):
    seed(client)

    def fire(event_id: str):
        return client.post(
            "/api/events",
            json={
                "event_id": event_id,
                "event_type": "subscription.pending",
                "subscription_id": "sub_priya",
                "occurred_at": at(hours=1),
            },
        ).json()

    with ThreadPoolExecutor(max_workers=2) as pool:
        first, second = list(pool.map(fire, ["evt_a", "evt_b"]))
    outcomes = {first["reason_code"], second["reason_code"]}
    assert "OK" in outcomes
    assert outcomes <= {"OK", "CONCURRENT_MODIFICATION", "NO_OP_SAME_STATE"}
    assert client.get("/api/subscriptions/sub_priya").json()["status"] == "pending"


def test_reconciliation_does_not_touch_another_run(client):
    seed(client, run_id="run_a", customer_id="cust_a", subscription_id="sub_a")
    send(client, "a1", "subscription.pending", at(hours=1), subscription_id="sub_a")
    send(client, "a2", "subscription.halted", at(hours=2), subscription_id="sub_a")
    send_invoice(
        client,
        "a3",
        "inv_a",
        "2026-02",
        months=1,
        occurred_at=at(hours=3),
        subscription_id="sub_a",
    )
    send(client, "a4", "subscription.activated", at(hours=4), subscription_id="sub_a")
    before = client.get("/api/recovery-cases", params={"run_id": "run_a"}).json()
    assert before
    scoped = client.post("/api/recovery-cases/reconcile", params={"run_id": "run_b"})
    assert scoped.status_code == 200
    after = client.get("/api/recovery-cases", params={"run_id": "run_a"}).json()
    assert [c["case_id"] for c in after] == [c["case_id"] for c in before]


def test_toctou_risk_flag_blocks_automated_action(client, mongo_uri, test_db_name):
    case = _open_case(
        client,
        card_type="international",
        customer_id="cust_risk",
        sub_id="sub_risk",
    )
    planned = client.post(f"/api/agent/cases/{case['case_id']}/plan", json={}).json()
    assert planned["recommended_action"] in {
        "send_payment_link",
        "attempt_manual_charge",
    }
    db = MongoClient(mongo_uri)[test_db_name]
    db.customers.update_one(
        {"customer_id": case["customer_id"]},
        {"$set": {"risk_flags": ["chargeback"]}},
    )
    executed = client.post(f"/api/agent/cases/{case['case_id']}/execute", json={}).json()
    assert executed["status"] == "escalated" or executed["stop_reason"] in {
        "POLICY_BLOCKED",
        "NO_AUTOMATED_ACTION",
    }
    executed_rows = list(
        db.recovery_actions.find({"case_id": case["case_id"], "status": "executed"})
    )
    assert executed_rows == []


def test_toctou_dispute_blocks_after_plan(client, mongo_uri, test_db_name):
    case = _open_case(
        client,
        card_type="international",
        customer_id="cust_mut_dis",
        sub_id="sub_mut_dis",
    )
    planned = client.post(f"/api/agent/cases/{case['case_id']}/plan", json={}).json()
    assert planned["recommended_action"] != "no_action"
    db = MongoClient(mongo_uri)[test_db_name]
    db.customers.update_one(
        {"customer_id": case["customer_id"]},
        {"$set": {"has_active_dispute": True}},
    )
    body = client.post(f"/api/agent/cases/{case['case_id']}/execute", json={}).json()
    assert body["stop_reason"] == "ACTIVE_DISPUTE"
    assert body["status"] == "escalated"
    assert list(db.recovery_actions.find({"case_id": case["case_id"], "status": "executed"})) == []


def test_closed_case_does_not_create_a_second_recovery(client, mongo_uri, test_db_name):
    case = _open_case(client, customer_id="cust_once", sub_id="sub_once")
    first = client.post(
        f"/api/agent/cases/{case['case_id']}/execute",
        json={"idempotency_key": "once-key"},
    ).json()
    if first.get("action") and first["action"].get("outcome") == "paid":
        second = client.post(
            f"/api/agent/cases/{case['case_id']}/execute",
            json={"idempotency_key": "once-key-2"},
        ).json()
        assert second["stop_reason"] in {"CASE_CLOSED", "ALREADY_EXECUTED"}
        db = MongoClient(mongo_uri)[test_db_name]
        paid = list(db.recovery_actions.find({"case_id": case["case_id"], "outcome": "paid"}))
        assert len(paid) == 1
        recovered = client.get(f"/api/recovery-cases/{case['case_id']}").json()
        assert recovered["case"]["amount_recovered_paise"] <= case["backlog_amount_paise"]


def test_system_failure_does_not_count_as_recovery(client, mongo_uri, test_db_name, monkeypatch):
    from app.agent import executor as executor_mod

    def boom(*_args, **_kwargs):
        raise RuntimeError("oracle unavailable")

    monkeypatch.setattr(executor_mod.SimulatedExecutor, "execute", boom)
    case = _open_case(client, customer_id="cust_sys", sub_id="sub_sys")
    body = client.post(f"/api/agent/cases/{case['case_id']}/execute", json={}).json()
    assert body["stop_reason"] == "SYSTEM_FAILURE"
    assert body.get("action") is None or body["action"].get("outcome") != "paid"
    refreshed = client.get(f"/api/recovery-cases/{case['case_id']}").json()
    assert refreshed["case"]["status"] == "open"
    assert refreshed["case"]["amount_recovered_paise"] == 0


def test_malformed_invoice_float_amount_still_refused(client):
    seed(client)
    res = client.post(
        "/api/events",
        json={
            "event_id": "inv_float",
            "event_type": "invoice.created",
            "subscription_id": "sub_priya",
            "occurred_at": at(hours=1),
            "payload": {
                **invoice_payload("inv_float", "2026-02", months=1),
                "amount_paise": 4999.5,
            },
        },
    )
    assert res.status_code in {422, 409}
