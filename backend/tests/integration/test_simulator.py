"""M3 simulator: world, baselines, isolation, API."""

from app.domain.enums import ActionType
from app.simulator.oracle import OracleCase, OutcomeOracle, latent_payment_intent
from tests.integration.helpers import RUN_ID

_ORACLE_ACTIONS = (
    ActionType.NO_ACTION,
    ActionType.SEND_PAYMENT_LINK,
    ActionType.ATTEMPT_MANUAL_CHARGE,
)
_CASE_FEATURES = (
    "backlog_amount_paise",
    "invoice_count",
    "halt_duration_days",
    "card_type",
    "risk_flags",
    "halt_episode_id",
    "historical_payment_success_rate",
    "previous_failure_count",
    "previous_halt_count",
    "subscription_age_days",
    "customer_opted_out",
    "has_active_dispute",
)

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


def _cases(client, run_id: str) -> dict[str, dict]:
    rows = client.get("/api/recovery-cases", params={"run_id": run_id}).json()
    by_key = {}
    for row in rows:
        key = row["synthetic_case_key"]
        assert key, row
        assert row["synthetic_customer_key"]
        by_key[key] = row
    return by_key


def _oracle_case(row: dict) -> OracleCase:
    return OracleCase(
        case_id=row["case_id"],
        synthetic_case_key=row["synthetic_case_key"],
        synthetic_customer_key=row["synthetic_customer_key"],
        backlog_amount_paise=row["backlog_amount_paise"],
        historical_payment_success_rate=row["historical_payment_success_rate"],
        has_dispute=row["has_active_dispute"],
        customer_opted_out=row["customer_opted_out"],
    )


def test_same_seed_reproduces_world_features_latent_and_oracle(client):
    a = _generate(client, seed=42)
    b = _generate(client, seed=42)
    assert a["run_id"] != b["run_id"]
    assert a["world_summary"] == b["world_summary"]

    cases_a = _cases(client, a["run_id"])
    cases_b = _cases(client, b["run_id"])
    assert set(cases_a) == set(cases_b)
    assert {c["case_id"] for c in cases_a.values()}.isdisjoint(
        {c["case_id"] for c in cases_b.values()}
    )
    assert {c["customer_id"] for c in cases_a.values()}.isdisjoint(
        {c["customer_id"] for c in cases_b.values()}
    )
    assert all(c["run_id"] == a["run_id"] for c in cases_a.values())
    assert all(c["run_id"] == b["run_id"] for c in cases_b.values())

    oracle = OutcomeOracle(42)
    for key, left in cases_a.items():
        right = cases_b[key]
        for field in _CASE_FEATURES:
            assert left[field] == right[field], (key, field)
        assert latent_payment_intent(42, left["synthetic_customer_key"]) == (
            latent_payment_intent(42, right["synthetic_customer_key"])
        )
        for action in _ORACLE_ACTIONS:
            assert oracle.decide(_oracle_case(left), action) == oracle.decide(
                _oracle_case(right), action
            )

    run_a = client.post(
        "/api/simulator/run",
        json={"run_id": a["run_id"], "strategies": ["naive", "rule_based"]},
    )
    run_b = client.post(
        "/api/simulator/run",
        json={"run_id": b["run_id"], "strategies": ["naive", "rule_based"]},
    )
    assert run_a.status_code == run_b.status_code == 200
    assert run_a.json()["strategy_results"] == run_b.json()["strategy_results"]

    again = client.post(
        "/api/simulator/run",
        json={"run_id": a["run_id"], "strategies": ["naive", "rule_based"]},
    )
    assert again.json()["strategy_results"] == run_a.json()["strategy_results"]


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
