from datetime import UTC, datetime, timedelta

from app.domain.enums import ActionType, CardType, PolicyReasonCode, Provenance
from app.domain.policy import PolicyContext, evaluate_policy
from app.policy import evaluate_v1
from app.policy.rules_v1 import mandate_cap

NOW = datetime(2026, 5, 1, 12, 0, tzinfo=UTC)


def ctx(**overrides) -> PolicyContext:
    base = dict(
        case_id="case_test",
        card_type=CardType.INTERNATIONAL,
        backlog_amount_paise=499900,
        mandate_max_amount_paise=499900,
        risk_flags=[],
        has_dispute=False,
        customer_opted_out=False,
        attempt_count=0,
        last_contact_at=None,
        now=NOW,
        max_attempts=3,
        contact_cooldown_hours=24,
    )
    base.update(overrides)
    return PolicyContext(**base)


def test_domestic_card_blocks_manual_charge():
    decision = evaluate_v1(ctx(card_type=CardType.DOMESTIC))
    assert ActionType.ATTEMPT_MANUAL_CHARGE in decision.blocked_actions
    assert ActionType.SEND_PAYMENT_LINK in decision.allowed_actions
    assert (
        PolicyReasonCode.DOMESTIC_CARD_MANUAL_CHARGE_UNSUPPORTED
        in decision.reason_codes
    )


def test_international_eligible_card_allows_manual_charge():
    decision = evaluate_v1(ctx(card_type=CardType.INTERNATIONAL))
    assert ActionType.ATTEMPT_MANUAL_CHARGE in decision.allowed_actions
    assert ActionType.SEND_PAYMENT_LINK in decision.allowed_actions
    assert decision.reason_codes == []


def test_mandate_cap_blocks_manual_charge():
    decision = evaluate_v1(
        ctx(
            card_type=CardType.INTERNATIONAL,
            backlog_amount_paise=1499700,
            mandate_max_amount_paise=499900,
        )
    )
    assert ActionType.ATTEMPT_MANUAL_CHARGE in decision.blocked_actions
    assert PolicyReasonCode.MANDATE_CAP_EXCEEDED in decision.reason_codes


def test_mandate_provenance_is_product_design_assumption():
    hit = mandate_cap(
        ctx(
            card_type=CardType.INTERNATIONAL,
            backlog_amount_paise=1499700,
            mandate_max_amount_paise=499900,
        )
    )
    assert hit is not None
    assert hit.provenance is Provenance.PRODUCT_DESIGN_ASSUMPTION
    assert hit.source_url is None

    decision = evaluate_v1(
        ctx(
            card_type=CardType.INTERNATIONAL,
            backlog_amount_paise=1499700,
            mandate_max_amount_paise=499900,
        )
    )
    rule = next(r for r in decision.applied_rules if r.rule_id == "mandate_cap")
    assert rule.provenance is Provenance.PRODUCT_DESIGN_ASSUMPTION


def test_risk_flag_escalates():
    decision = evaluate_v1(ctx(risk_flags=["chargeback"]))
    assert decision.requires_escalation is True
    assert ActionType.SEND_PAYMENT_LINK in decision.blocked_actions
    assert ActionType.ATTEMPT_MANUAL_CHARGE in decision.blocked_actions
    assert ActionType.ESCALATE_TO_MERCHANT in decision.allowed_actions
    assert PolicyReasonCode.RISK_FLAG_PRESENT in decision.reason_codes


def test_dispute_stops_automation():
    decision = evaluate_v1(ctx(has_dispute=True))
    assert decision.stop is True
    assert decision.requires_escalation is True
    assert ActionType.SEND_PAYMENT_LINK in decision.blocked_actions
    assert ActionType.ATTEMPT_MANUAL_CHARGE in decision.blocked_actions
    assert ActionType.ESCALATE_TO_MERCHANT in decision.allowed_actions
    assert ActionType.NO_ACTION in decision.allowed_actions
    assert PolicyReasonCode.ACTIVE_DISPUTE in decision.reason_codes


def test_opt_out_blocks_contact():
    decision = evaluate_v1(ctx(customer_opted_out=True))
    assert ActionType.SEND_PAYMENT_LINK in decision.blocked_actions
    assert decision.requires_escalation is True
    assert PolicyReasonCode.CUSTOMER_OPTED_OUT in decision.reason_codes


def test_max_attempts_escalates():
    decision = evaluate_v1(ctx(attempt_count=3, max_attempts=3))
    assert decision.requires_escalation is True
    assert ActionType.SEND_PAYMENT_LINK in decision.blocked_actions
    assert ActionType.ATTEMPT_MANUAL_CHARGE in decision.blocked_actions
    assert PolicyReasonCode.MAX_ATTEMPTS_REACHED in decision.reason_codes


def test_contact_cooldown_blocks_contact():
    last = NOW - timedelta(hours=2)
    decision = evaluate_v1(ctx(last_contact_at=last, contact_cooldown_hours=24))
    assert ActionType.SEND_PAYMENT_LINK in decision.blocked_actions
    assert PolicyReasonCode.CONTACT_COOLDOWN_ACTIVE in decision.reason_codes


def test_injected_time_controls_cooldown():
    last = datetime(2026, 5, 1, 10, 0, tzinfo=UTC)
    still_cooling = evaluate_v1(
        ctx(last_contact_at=last, now=last + timedelta(hours=6), contact_cooldown_hours=24)
    )
    cooled = evaluate_v1(
        ctx(last_contact_at=last, now=last + timedelta(hours=25), contact_cooldown_hours=24)
    )
    assert PolicyReasonCode.CONTACT_COOLDOWN_ACTIVE in still_cooling.reason_codes
    assert PolicyReasonCode.CONTACT_COOLDOWN_ACTIVE not in cooled.reason_codes
    assert ActionType.SEND_PAYMENT_LINK in cooled.allowed_actions


def test_multiple_rules_accumulate_reason_codes():
    decision = evaluate_v1(
        ctx(
            card_type=CardType.DOMESTIC,
            backlog_amount_paise=1499700,
            mandate_max_amount_paise=499900,
            risk_flags=["high_risk"],
        )
    )
    assert set(decision.reason_codes) == {
        PolicyReasonCode.DOMESTIC_CARD_MANUAL_CHARGE_UNSUPPORTED,
        PolicyReasonCode.MANDATE_CAP_EXCEEDED,
        PolicyReasonCode.RISK_FLAG_PRESENT,
    }
    assert decision.requires_escalation is True
    assert ActionType.ATTEMPT_MANUAL_CHARGE in decision.blocked_actions
    assert ActionType.SEND_PAYMENT_LINK in decision.blocked_actions


def test_policy_evaluation_is_deterministic():
    context = ctx(
        card_type=CardType.DOMESTIC,
        backlog_amount_paise=1499700,
        mandate_max_amount_paise=499900,
        risk_flags=["x"],
        has_dispute=True,
    )
    first = evaluate_v1(context)
    second = evaluate_v1(context)
    assert first.model_dump() == second.model_dump()


def test_equal_mandate_does_not_block():
    """The rule is strictly greater-than. Equal to the cap is still chargeable."""
    decision = evaluate_v1(
        ctx(
            card_type=CardType.INTERNATIONAL,
            backlog_amount_paise=499900,
            mandate_max_amount_paise=499900,
        )
    )
    assert ActionType.ATTEMPT_MANUAL_CHARGE in decision.allowed_actions


def test_empty_rule_set_allows_the_default_actions():
    """Sanity: the evaluator itself does not invent blocks."""
    decision = evaluate_policy(ctx(), rules=())
    assert decision.blocked_actions == []
    assert decision.allowed_actions == list(
        [
            ActionType.NO_ACTION,
            ActionType.SEND_PAYMENT_LINK,
            ActionType.ATTEMPT_MANUAL_CHARGE,
            ActionType.ESCALATE_TO_MERCHANT,
        ]
    )
