"""M3 simulator: world, baselines, isolation, API."""

from tests.integration.helpers import RUN_ID

SMALL = {
    "subscriber_count": 24,
    "seed": 42,
    "intervention_budget": 8,
    "min_missed_cycles": 1,
    "max_missed_cycles": 3,
}


def _generate(client, **overrides):
    body = {**SMALL, **overrides}
    r = client.post("/api/simulator/generate", json=body)
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["synthetic"] is True
    return data


def test_generate_and_get_run(client):
    created = _generate(client)
    run_id = created["run_id"]
    got = client.get(f"/api/runs/{run_id}")
    assert got.status_code == 200
    body = got.json()
    assert body["synthetic"] is True
    assert body["run_id"] == run_id
    assert body["world_summary"]["subscriber_count"] == 24
    assert body["world_summary"]["recovery_case_count"] >= 1
    assert body["world_summary"]["always_active_count"] >= 1
    assert body["world_summary"]["halted_never_returned_count"] >= 1
    assert body["world_summary"]["reactivated_count"] >= 1


def test_same_seed_same_world_summary(client):
    a = _generate(client, seed=42)
    b = _generate(client, seed=42)
    sa, sb = a["world_summary"], b["world_summary"]
    for key in (
        "subscriber_count",
        "always_active_count",
        "halted_never_returned_count",
        "reactivated_count",
        "recovery_case_count",
        "revenue_at_risk_paise",
        "domestic_card_count",
        "international_card_count",
    ):
        assert sa[key] == sb[key], key
    assert a["run_id"] != b["run_id"]


def test_different_seed_changes_world(client):
    a = _generate(client, seed=42)
    b = _generate(client, seed=43)
    assert a["world_summary"] != b["world_summary"]


def test_run_isolation(client):
    a = _generate(client, seed=11)
    b = _generate(client, seed=12)
    cases_a = client.get("/api/recovery-cases", params={"run_id": a["run_id"]}).json()
    cases_b = client.get("/api/recovery-cases", params={"run_id": b["run_id"]}).json()
    ids_a = {c["case_id"] for c in cases_a}
    ids_b = {c["case_id"] for c in cases_b}
    assert ids_a.isdisjoint(ids_b)
    assert all(c["run_id"] == a["run_id"] for c in cases_a)
    # M2 leftover run_test must not appear in either.
    assert RUN_ID not in {c["run_id"] for c in cases_a + cases_b}


def test_only_reactivated_backlog_creates_cases(client):
    world = _generate(client, seed=42)
    summary = world["world_summary"]
    cases = client.get(
        "/api/recovery-cases", params={"run_id": world["run_id"]}
    ).json()
    assert len(cases) == summary["recovery_case_count"]
    assert len(cases) <= summary["reactivated_count"] * 2  # second halt possible
    assert all(c["backlog_amount_paise"] > 0 for c in cases)
    assert all(isinstance(c["backlog_amount_paise"], int) for c in cases)


def test_simulator_run_baselines_share_world_and_respect_budget_and_policy(client):
    world = _generate(client, seed=42, intervention_budget=8)
    run_id = world["run_id"]
    executed = client.post(
        "/api/simulator/run",
        json={"run_id": run_id, "strategies": ["naive", "rule_based"]},
    )
    assert executed.status_code == 200, executed.text
    body = executed.json()
    assert body["synthetic"] is True
    naive = body["strategy_results"]["naive"]
    rule = body["strategy_results"]["rule_based"]
    assert naive["eligible_cases"] == rule["eligible_cases"]
    assert naive["intervention_budget"] == rule["intervention_budget"] == 8
    assert naive["interventions_used"] <= 8
    assert rule["interventions_used"] <= 8
    assert naive["revenue_at_risk_paise"] == rule["revenue_at_risk_paise"]
    assert isinstance(naive["revenue_recovered_paise"], int)
    assert isinstance(rule["incremental_revenue_paise"], int)

    again = client.post(
        "/api/simulator/run",
        json={"run_id": run_id, "strategies": ["naive", "rule_based"]},
    )
    assert again.json()["strategy_results"] == body["strategy_results"]

    stored = client.get(f"/api/runs/{run_id}").json()
    assert stored["strategy_results"]["naive"]["revenue_recovered_paise"] == naive[
        "revenue_recovered_paise"
    ]


def test_m3_e2e_hundred_subscribers(client):
    world = _generate(
        client,
        subscriber_count=100,
        seed=42,
        intervention_budget=25,
        min_missed_cycles=1,
        max_missed_cycles=6,
    )
    summary = world["world_summary"]
    assert summary["subscriber_count"] == 100
    assert summary["recovery_case_count"] >= 1
    assert summary["synthetic"] is True

    executed = client.post(
        "/api/simulator/run",
        json={"run_id": world["run_id"], "strategies": ["naive", "rule_based"]},
    )
    assert executed.status_code == 200, executed.text
    results = executed.json()["strategy_results"]
    assert set(results) == {"naive", "rule_based"}
    for _name, metrics in results.items():
        assert metrics["intervention_budget"] == 25
        assert metrics["interventions_used"] <= 25
        assert metrics["eligible_cases"] == summary["recovery_case_count"]
        assert metrics["synthetic"] is True
        assert isinstance(metrics["revenue_recovered_paise"], int)
