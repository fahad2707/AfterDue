"""Collectibility gate: entitlement before recovery economics."""

from tests.integration.helpers import at, get_audit, seed, send, send_invoice
from tests.integration.test_simulator import _generate

MAY_JUNE_JULY = 500_000  # ₹5,000.00


def test_suspend_on_halt_world_has_no_collectible_optimization(client):
    world = _generate(
        client,
        subscriber_count=8,
        seed=7,
        halt_rate=1.0,
        reactivation_rate=1.0,
        suspend_on_halt_rate=1.0,
        continue_during_grace_rate=0.0,
        min_missed_cycles=3,
        max_missed_cycles=3,
        intervention_budget=8,
    )
    summary = world["world_summary"]
    assert summary["historical_unpaid_amount_paise"] > 0
    assert summary["collectible_amount_paise"] == 0
    assert summary["revenue_at_risk_paise"] == 0
    assert summary["collectible_recovery_case_count"] == 0

    cases = client.get(
        "/api/recovery-cases", params={"run_id": world["run_id"]}
    ).json()
    assert all(c["backlog_amount_paise"] == c["collectible_amount_paise"] for c in cases)
    assert all(c["collectible_amount_paise"] == 0 for c in cases)
    assert all(c.get("model_analysis") in (None, {}) for c in cases)

    executed = client.post(
        "/api/simulator/run",
        json={"run_id": world["run_id"], "strategies": ["naive", "rule_based"]},
    )
    assert executed.status_code == 200, executed.text
    results = executed.json()["strategy_results"]
    assert results["naive"]["eligible_cases"] == 0
    assert results["rule_based"]["eligible_cases"] == 0
    assert results["naive"]["revenue_at_risk_paise"] == 0
    assert results["rule_based"]["revenue_recovered_paise"] == 0


def test_continue_during_grace_enters_existing_pipeline(client):
    world = _generate(
        client,
        subscriber_count=8,
        seed=11,
        halt_rate=1.0,
        reactivation_rate=1.0,
        suspend_on_halt_rate=0.0,
        continue_during_grace_rate=1.0,
        grace_cycles=6,
        min_missed_cycles=3,
        max_missed_cycles=3,
        intervention_budget=8,
    )
    summary = world["world_summary"]
    assert summary["collectible_amount_paise"] > 0
    assert summary["collectible_amount_paise"] == summary["historical_unpaid_amount_paise"]
    assert summary["collectible_recovery_case_count"] >= 1
    assert summary["review_required_amount_paise"] == 0
    assert summary["not_collectible_amount_paise"] == 0

    cases = client.get(
        "/api/recovery-cases", params={"run_id": world["run_id"]}
    ).json()
    open_cases = [c for c in cases if c["status"] != "review_required"]
    assert open_cases
    assert all(c["backlog_amount_paise"] == c["collectible_amount_paise"] for c in open_cases)
    assert all(c["collectible_amount_paise"] > 0 for c in open_cases)
    assert all(
        "send_payment_link" in c["allowed_actions"]
        or c["stop"]
        or c["requires_escalation"]
        for c in open_cases
    )

    executed = client.post(
        "/api/simulator/run",
        json={"run_id": world["run_id"], "strategies": ["naive", "rule_based"]},
    )
    assert executed.status_code == 200, executed.text
    results = executed.json()["strategy_results"]
    assert results["naive"]["eligible_cases"] == results["rule_based"]["eligible_cases"]
    assert results["naive"]["eligible_cases"] == summary["collectible_recovery_case_count"]
    naive_at_risk = results["naive"]["revenue_at_risk_paise"]
    rule_at_risk = results["rule_based"]["revenue_at_risk_paise"]
    assert naive_at_risk == rule_at_risk
    assert results["naive"]["revenue_at_risk_paise"] == summary["revenue_at_risk_paise"]


def test_mandatory_mixed_may_june_july_collectibility(client):
    seed(client)
    send(client, "e1", "subscription.pending", at(hours=1))
    send(client, "e2", "subscription.halted", at(hours=2))
    months = [
        ("inv_may", "2026-05", 4, "delivered"),
        ("inv_jun", "2026-06", 5, "suspended"),
        ("inv_jul", "2026-07", 6, "unknown"),
    ]
    for i, (invoice_id, cycle, month, delivery) in enumerate(months):
        send_invoice(
            client,
            f"i{i+1}",
            invoice_id,
            cycle,
            months=month,
            occurred_at=at(hours=3 + i),
            amount=MAY_JUNE_JULY,
            service_delivery_status=delivery,
        )
    send(client, "e3", "subscription.activated", at(hours=20))

    cases = client.get("/api/recovery-cases", params={"run_id": "run_test"}).json()
    assert len(cases) == 1
    case = cases[0]
    assert case["historical_unpaid_amount_paise"] == 1_500_000
    assert case["collectible_amount_paise"] == MAY_JUNE_JULY
    assert case["not_collectible_amount_paise"] == MAY_JUNE_JULY
    assert case["review_required_amount_paise"] == MAY_JUNE_JULY
    assert case["backlog_amount_paise"] == MAY_JUNE_JULY
    assert case["backlog_amount_paise"] == case["collectible_amount_paise"]
    assert case["invoice_count"] == 1
    assert case["invoice_ids"] == ["inv_may"]
    assert case["collectible_invoice_ids"] == ["inv_may"]
    assert case["not_collectible_invoice_ids"] == ["inv_jun"]
    assert case["review_required_invoice_ids"] == ["inv_jul"]
    assert case["status"] == "open"
    assert type(case["backlog_amount_paise"]) is int

    detail = client.get(f"/api/recovery-cases/{case['case_id']}").json()
    by_id = {row["invoice_id"]: row for row in detail["invoices"]}
    assert set(by_id) == {"inv_may", "inv_jun", "inv_jul"}
    assert by_id["inv_may"]["service_delivery_status"] == "delivered"
    assert by_id["inv_may"]["collectibility_status"] == "collectible"
    assert by_id["inv_jun"]["service_delivery_status"] == "suspended"
    assert by_id["inv_jun"]["collectibility_status"] == "not_collectible"
    assert by_id["inv_jul"]["service_delivery_status"] == "unknown"
    assert by_id["inv_jul"]["collectibility_status"] == "review_required"
    assert detail["model_analysis"] is None or (
        detail["case"]["backlog_amount_paise"] == MAY_JUNE_JULY
    )

    audit = get_audit(client)
    kinds = [a["event_type"] for a in audit]
    assert "COLLECTIBILITY_EVALUATED" in kinds
    assert "INVOICE_MARKED_COLLECTIBLE" in kinds
    assert "INVOICE_EXCLUDED_NON_COLLECTIBLE" in kinds
    assert "INVOICE_REVIEW_REQUIRED" in kinds
    evaluated = next(a for a in audit if a["event_type"] == "COLLECTIBILITY_EVALUATED")
    assert evaluated["details"]["historical_unpaid_amount_paise"] == 1_500_000
    assert evaluated["details"]["collectible_amount_paise"] == MAY_JUNE_JULY
    assert evaluated["details"]["not_collectible_amount_paise"] == MAY_JUNE_JULY
    assert evaluated["details"]["review_required_amount_paise"] == MAY_JUNE_JULY
    reconstructed = next(a for a in audit if a["event_type"] == "BACKLOG_RECONSTRUCTED")
    assert reconstructed["details"]["historical_unpaid_amount_paise"] == 1_500_000


def test_all_suspended_invoices_create_no_automatic_case(client):
    seed(client)
    send(client, "e1", "subscription.pending", at(hours=1))
    send(client, "e2", "subscription.halted", at(hours=2))
    for i in range(3):
        send_invoice(
            client,
            f"i{i+1}",
            f"inv_{i+1}",
            f"2026-0{i+2}",
            months=i + 1,
            occurred_at=at(hours=3 + i),
            service_delivery_status="suspended",
        )
    send(client, "e3", "subscription.activated", at(hours=10))
    cases = client.get("/api/recovery-cases", params={"run_id": "run_test"}).json()
    assert cases == []
    kinds = [a["event_type"] for a in get_audit(client)]
    assert "COLLECTIBILITY_EVALUATED" in kinds
    assert "RECOVERY_CASE_CREATED" not in kinds
    assert "INVOICE_EXCLUDED_NON_COLLECTIBLE" in kinds


def test_strategies_share_identical_post_collectibility_universe(client):
    world = _generate(
        client,
        subscriber_count=20,
        seed=21,
        intervention_budget=8,
        suspend_on_halt_rate=0.3,
        continue_during_grace_rate=0.4,
    )
    executed = client.post(
        "/api/simulator/run",
        json={"run_id": world["run_id"], "strategies": ["naive", "rule_based"]},
    )
    assert executed.status_code == 200, executed.text
    naive = executed.json()["strategy_results"]["naive"]
    rule = executed.json()["strategy_results"]["rule_based"]
    summary = world["world_summary"]
    assert naive["eligible_cases"] == rule["eligible_cases"]
    assert naive["eligible_cases"] == summary["collectible_recovery_case_count"]
    assert naive["revenue_at_risk_paise"] == rule["revenue_at_risk_paise"]
    assert naive["revenue_at_risk_paise"] == summary["revenue_at_risk_paise"]
    assert naive["revenue_at_risk_paise"] == summary["collectible_amount_paise"]
    assert type(naive["revenue_at_risk_paise"]) is int
