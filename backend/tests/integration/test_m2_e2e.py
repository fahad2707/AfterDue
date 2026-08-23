"""End-to-end M2 cases: Priya (domestic) and an international counterpart."""

from tests.integration.helpers import PLAN_PAISE, seed, send


def test_priya_domestic_three_invoice_backlog(client):
    """₹4,999 × 3 = 1,499,700 paise. Manual charge blocked. No execution."""
    seed(client, name="Priya Sharma", card_type="domestic")

    send(client, "e_pending", "subscription.pending", "2026-01-15T10:00:00+00:00")
    send(client, "e_halted", "subscription.halted", "2026-02-01T10:00:00+00:00")

    for event_id, invoice_id, cycle, occurred, start, end in (
        (
            "i_feb",
            "inv_feb",
            "2026-02",
            "2026-02-10T10:00:00+00:00",
            "2026-02-01T00:00:00+00:00",
            "2026-02-28T00:00:00+00:00",
        ),
        (
            "i_mar",
            "inv_mar",
            "2026-03",
            "2026-03-10T10:00:00+00:00",
            "2026-03-01T00:00:00+00:00",
            "2026-03-31T00:00:00+00:00",
        ),
        (
            "i_apr",
            "inv_apr",
            "2026-04",
            "2026-04-10T10:00:00+00:00",
            "2026-04-01T00:00:00+00:00",
            "2026-04-30T00:00:00+00:00",
        ),
    ):
        r = send(
            client,
            event_id,
            "invoice.created",
            occurred,
            {
                "invoice_id": invoice_id,
                "billing_cycle": cycle,
                "period_start": start,
                "period_end": end,
                "amount_paise": PLAN_PAISE,
            },
        )
        assert r.status_code == 200, r.text

    activated = send(
        client, "e_active", "subscription.activated", "2026-05-02T10:00:00+00:00"
    )
    assert activated.status_code == 200, activated.text
    assert activated.json()["outcome"] == "processed"

    sub = client.get("/api/subscriptions/sub_priya").json()
    assert sub["status"] == "active"
    assert len(sub["halt_episodes"]) == 1
    episode = sub["halt_episodes"][0]
    assert episode["reactivated_at"] is not None
    assert set(episode["invoice_ids"]) == {"inv_feb", "inv_mar", "inv_apr"}

    cases = client.get("/api/recovery-cases", params={"run_id": "run_test"}).json()
    assert len(cases) == 1
    case = cases[0]
    assert case["invoice_count"] == 3
    assert case["backlog_amount_paise"] == 1_499_700
    assert case["backlog_amount_display"] == "₹14,997.00"
    assert case["halt_duration_days"] == 90
    assert case["status"] == "open"

    detail = client.get(f"/api/recovery-cases/{case['case_id']}")
    assert detail.status_code == 200, detail.text
    body = detail.json()
    assert {i["invoice_id"] for i in body["invoices"]} == {
        "inv_feb",
        "inv_mar",
        "inv_apr",
    }
    assert all(i["halt_episode_id"] == "he_1" for i in body["invoices"])

    policy = body["policy"]
    assert "attempt_manual_charge" in policy["blocked_actions"]
    assert "send_payment_link" in policy["allowed_actions"]
    assert "DOMESTIC_CARD_MANUAL_CHARGE_UNSUPPORTED" in policy["reason_codes"]
    # Mandate cap also applies (backlog > plan). Composition must keep both.
    assert "MANDATE_CAP_EXCEEDED" in policy["reason_codes"]

    audit = client.get(f"/api/recovery-cases/{case['case_id']}/audit").json()
    kinds = [a["event_type"] for a in audit]
    for required in (
        "HALT_EPISODE_CLOSED",
        "RECOVERY_WINDOW_OPENED",
        "BACKLOG_RECONSTRUCTED",
        "RECOVERY_CASE_CREATED",
        "POLICY_EVALUATED",
    ):
        assert required in kinds, kinds
    assert kinds.index("HALT_EPISODE_CLOSED") < kinds.index("RECOVERY_WINDOW_OPENED")
    assert kinds.index("RECOVERY_WINDOW_OPENED") < kinds.index("BACKLOG_RECONSTRUCTED")
    assert kinds.index("BACKLOG_RECONSTRUCTED") < kinds.index("RECOVERY_CASE_CREATED")
    assert kinds.index("RECOVERY_CASE_CREATED") < kinds.index("POLICY_EVALUATED")
    assert "ACTION_EXECUTED" not in kinds


def test_international_card_allows_manual_charge(client):
    seed(
        client,
        name="Arjun Mehta",
        card_type="international",
        customer_id="cust_arjun",
        subscription_id="sub_arjun",
        mandate_max_amount_paise=2_000_000,
    )
    send(
        client,
        "e1",
        "subscription.pending",
        "2026-02-01T10:00:00+00:00",
        subscription_id="sub_arjun",
    )
    send(
        client,
        "e2",
        "subscription.halted",
        "2026-02-05T10:00:00+00:00",
        subscription_id="sub_arjun",
    )
    send(
        client,
        "i1",
        "invoice.created",
        "2026-03-01T10:00:00+00:00",
        {
            "invoice_id": "inv_arjun_mar",
            "billing_cycle": "2026-03",
            "period_start": "2026-03-01T00:00:00+00:00",
            "period_end": "2026-03-31T00:00:00+00:00",
            "amount_paise": PLAN_PAISE,
        },
        subscription_id="sub_arjun",
    )
    send(
        client,
        "e3",
        "subscription.activated",
        "2026-03-20T10:00:00+00:00",
        subscription_id="sub_arjun",
    )

    cases = client.get("/api/recovery-cases", params={"run_id": "run_test"}).json()
    assert len(cases) == 1
    detail = client.get(f"/api/recovery-cases/{cases[0]['case_id']}").json()
    policy = detail["policy"]
    assert "attempt_manual_charge" in policy["allowed_actions"]
    assert "send_payment_link" in policy["allowed_actions"]
    assert "DOMESTIC_CARD_MANUAL_CHARGE_UNSUPPORTED" not in policy["reason_codes"]
    assert "MANDATE_CAP_EXCEEDED" not in policy["reason_codes"]
    assert policy["stop"] is False
    assert policy["requires_escalation"] is False


def test_policy_dry_run_does_not_create_a_case(client):
    before = client.get("/api/recovery-cases", params={"run_id": "run_test"}).json()
    r = client.post(
        "/api/policy/evaluate",
        json={
            "case_id": "case_dry",
            "card_type": "domestic",
            "backlog_amount_paise": 1499700,
            "mandate_max_amount_paise": 499900,
            "now": "2026-05-01T12:00:00+00:00",
        },
    )
    assert r.status_code == 200, r.text
    assert "attempt_manual_charge" in r.json()["blocked_actions"]
    after = client.get("/api/recovery-cases", params={"run_id": "run_test"}).json()
    assert after == before


def test_policy_config_exposes_provenance_without_secrets(client):
    r = client.get("/api/policy/config")
    assert r.status_code == 200
    body = r.json()
    assert body["policy_version"] == "v1"
    assert "ANTHROPIC" not in str(body)
    mandate = next(rule for rule in body["rules"] if rule["rule_id"] == "mandate_cap")
    assert mandate["provenance"] == "PRODUCT_DESIGN_ASSUMPTION"
    assert mandate["source_url"] is None
