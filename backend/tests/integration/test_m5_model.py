"""M5 APIs and fair three-strategy comparison. Uses a throwaway artifact path."""

from tests.integration.test_simulator import _generate


def test_reclaim_without_model_is_a_clear_error(client):
    created = _generate(client)
    res = client.post(
        "/api/simulator/run",
        json={"run_id": created["run_id"], "strategies": ["reclaim"]},
    )
    assert res.status_code == 409
    assert "model" in res.json()["detail"].lower()
    assert "rule" not in res.json()["detail"].lower()


def test_train_evaluate_active_and_three_strategies(client):
    trained = client.post(
        "/api/model/train",
        json={"dataset_seed": 42, "n_examples": 800},
    )
    assert trained.status_code == 200, trained.text
    body = trained.json()
    assert body["synthetic"] is True
    assert body["is_active"] is True
    assert body["feature_schema_hash"]
    assert "brier" in body["metrics"]
    assert body["model_type"] in {"logistic_regression", "hist_gradient_boosting"}

    active = client.get("/api/model/active")
    assert active.status_code == 200
    assert active.json()["model_run_id"] == body["model_run_id"]

    metrics = client.get("/api/model/metrics")
    assert metrics.status_code == 200
    assert metrics.json()["metrics"]["brier"] >= 0

    evaluated = client.post("/api/model/evaluate", json={"dataset_seed": 42, "n_examples": 800})
    assert evaluated.status_code == 200
    assert "brier" in evaluated.json()["metrics"]

    created = _generate(client, subscriber_count=30, seed=42, intervention_budget=8)
    run_id = created["run_id"]
    first = client.post(
        "/api/simulator/run",
        json={"run_id": run_id, "strategies": ["naive", "rule_based", "reclaim"]},
    )
    assert first.status_code == 200, first.text
    results = first.json()["strategy_results"]
    assert set(results) == {"naive", "rule_based", "reclaim"}
    for _name, row in results.items():
        assert row["intervention_budget"] == 8
        assert row["interventions_used"] <= 8
        assert row["eligible_cases"] == results["naive"]["eligible_cases"]
        assert row["revenue_at_risk_paise"] == results["naive"]["revenue_at_risk_paise"]
        assert isinstance(row["revenue_recovered_paise"], int)
        assert isinstance(row["incremental_revenue_paise"], int)
        assert row["synthetic"] is True

    second = client.post(
        "/api/simulator/run",
        json={"run_id": run_id, "strategies": ["naive", "rule_based", "reclaim"]},
    )
    assert second.json()["strategy_results"] == results

    cases = client.get("/api/recovery-cases", params={"run_id": run_id}).json()
    analyzed = [row for row in cases if row.get("model_analysis")]
    assert analyzed
    sample = analyzed[0]
    analysis = sample["model_analysis"]
    assert "p_no_action" in analysis
    assert "expected_incremental_recovery_paise" in analysis
    assert isinstance(analysis["expected_incremental_recovery_paise"], int)
    if "attempt_manual_charge" in sample["blocked_actions"]:
        assert analysis["selected_action"] != "attempt_manual_charge"
        assert all(c["action"] != "attempt_manual_charge" for c in analysis["candidates"])

    detail = client.get(f"/api/recovery-cases/{sample['case_id']}").json()
    assert detail["model_analysis"]["model_version"] == analysis["model_version"]

    summary = client.get("/api/dashboard/summary", params={"run_id": run_id}).json()
    assert "reclaim" in summary["strategy_results"]
    assert summary["best_baseline_name"] in {"naive", "rule_based"}
    assert summary["reclaim_vs_best_baseline_paise"] is not None
