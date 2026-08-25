"""Collectibility engine: entitlement is deterministic, not predicted."""

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from app.domain.collectibility import (
    CollectibilitySubject,
    evaluate_collectibility,
    evaluate_collectibility_for_invoices,
)
from app.domain.enums import (
    CardType,
    CollectibilityReasonCode,
    CollectibilityStatus,
    InvoiceStatus,
    RecoveryCaseStatus,
    ServiceDeliveryStatus,
)
from app.models.documents import RecoveryCase
from app.schemas.events import InvoiceCreatedPayload

T0 = datetime(2026, 1, 1, tzinfo=UTC)


def _subject(
    invoice_id: str = "inv_1",
    *,
    status: InvoiceStatus = InvoiceStatus.ISSUED_UNPAID,
    amount: int = 500000,
    delivery: ServiceDeliveryStatus = ServiceDeliveryStatus.DELIVERED,
    waived: bool = False,
    merchant_marked_non_collectible: bool = False,
) -> CollectibilitySubject:
    return CollectibilitySubject(
        invoice_id=invoice_id,
        status=status,
        amount_paise=amount,
        service_delivery_status=delivery,
        waived=waived,
        merchant_marked_non_collectible=merchant_marked_non_collectible,
    )


def test_delivered_unpaid_is_collectible_full_amount():
    decision = evaluate_collectibility(_subject(delivery=ServiceDeliveryStatus.DELIVERED))
    assert decision.status is CollectibilityStatus.COLLECTIBLE
    assert decision.reason_codes == (CollectibilityReasonCode.SERVICE_DELIVERED,)
    assert decision.eligible_amount_paise == 500000
    assert type(decision.eligible_amount_paise) is int


def test_suspended_unpaid_is_not_collectible():
    decision = evaluate_collectibility(_subject(delivery=ServiceDeliveryStatus.SUSPENDED))
    assert decision.status is CollectibilityStatus.NOT_COLLECTIBLE
    assert decision.reason_codes == (CollectibilityReasonCode.SERVICE_SUSPENDED,)
    assert decision.eligible_amount_paise == 0


def test_unknown_unpaid_fails_closed_to_review_required():
    decision = evaluate_collectibility(_subject(delivery=ServiceDeliveryStatus.UNKNOWN))
    assert decision.status is CollectibilityStatus.REVIEW_REQUIRED
    assert decision.reason_codes == (CollectibilityReasonCode.SERVICE_DELIVERY_UNKNOWN,)
    assert decision.eligible_amount_paise == 0


def test_missing_delivery_defaults_to_unknown_via_subject():
    subject = CollectibilitySubject(
        invoice_id="inv_missing",
        status=InvoiceStatus.ISSUED_UNPAID,
        amount_paise=100,
    )
    assert subject.service_delivery_status is ServiceDeliveryStatus.UNKNOWN
    decision = evaluate_collectibility(subject)
    assert decision.status is CollectibilityStatus.REVIEW_REQUIRED
    assert decision.eligible_amount_paise == 0


def test_partially_delivered_is_review_required_no_proportional_split():
    decision = evaluate_collectibility(
        _subject(amount=999900, delivery=ServiceDeliveryStatus.PARTIALLY_DELIVERED)
    )
    assert decision.status is CollectibilityStatus.REVIEW_REQUIRED
    assert decision.reason_codes == (CollectibilityReasonCode.SERVICE_PARTIALLY_DELIVERED,)
    assert decision.eligible_amount_paise == 0


def test_paid_invoice_never_contributes_recovery_value():
    decision = evaluate_collectibility(
        _subject(status=InvoiceStatus.PAID, delivery=ServiceDeliveryStatus.DELIVERED)
    )
    assert decision.status is CollectibilityStatus.NOT_COLLECTIBLE
    assert decision.reason_codes == (CollectibilityReasonCode.INVOICE_ALREADY_PAID,)
    assert decision.eligible_amount_paise == 0


def test_waived_invoice_is_not_collectible():
    decision = evaluate_collectibility(_subject(waived=True))
    assert decision.status is CollectibilityStatus.NOT_COLLECTIBLE
    assert decision.reason_codes == (CollectibilityReasonCode.INVOICE_WAIVED,)
    assert decision.eligible_amount_paise == 0


def test_merchant_marked_non_collectible():
    decision = evaluate_collectibility(_subject(merchant_marked_non_collectible=True))
    assert decision.status is CollectibilityStatus.NOT_COLLECTIBLE
    assert (
        decision.reason_codes
        == (CollectibilityReasonCode.MERCHANT_MARKED_NON_COLLECTIBLE,)
    )


def test_all_suspended_mixture_has_zero_collectible():
    result = evaluate_collectibility_for_invoices(
        [
            _subject("a", delivery=ServiceDeliveryStatus.SUSPENDED, amount=500000),
            _subject("b", delivery=ServiceDeliveryStatus.SUSPENDED, amount=500000),
            _subject("c", delivery=ServiceDeliveryStatus.SUSPENDED, amount=500000),
        ]
    )
    assert result.historical_unpaid_amount_paise == 1_500_000
    assert result.collectible_amount_paise == 0
    assert result.not_collectible_amount_paise == 1_500_000
    assert result.review_required_amount_paise == 0
    assert result.collectible_invoice_ids == []
    assert result.case_collectibility_status is CollectibilityStatus.NOT_COLLECTIBLE


def test_mixture_two_delivered_one_suspended():
    result = evaluate_collectibility_for_invoices(
        [
            _subject("may", delivery=ServiceDeliveryStatus.DELIVERED, amount=500000),
            _subject("jun", delivery=ServiceDeliveryStatus.DELIVERED, amount=500000),
            _subject("jul", delivery=ServiceDeliveryStatus.SUSPENDED, amount=500000),
        ]
    )
    assert result.historical_unpaid_invoice_ids == ["may", "jun", "jul"]
    assert len(result.historical_unpaid_invoice_ids) == 3
    assert result.collectible_invoice_ids == ["may", "jun"]
    assert result.not_collectible_invoice_ids == ["jul"]
    assert result.historical_unpaid_amount_paise == 1_500_000
    assert result.collectible_amount_paise == 1_000_000
    assert result.not_collectible_amount_paise == 500000
    assert result.review_required_amount_paise == 0
    assert type(result.collectible_amount_paise) is int


def test_mandatory_mixed_may_june_july():
    """₹5,000 delivered + ₹5,000 suspended + ₹5,000 unknown."""
    result = evaluate_collectibility_for_invoices(
        [
            _subject("may", delivery=ServiceDeliveryStatus.DELIVERED, amount=500000),
            _subject("jun", delivery=ServiceDeliveryStatus.SUSPENDED, amount=500000),
            _subject("jul", delivery=ServiceDeliveryStatus.UNKNOWN, amount=500000),
        ]
    )
    assert result.historical_unpaid_amount_paise == 1_500_000
    assert result.collectible_amount_paise == 500000
    assert result.not_collectible_amount_paise == 500000
    assert result.review_required_amount_paise == 500000
    assert result.collectible_invoice_ids == ["may"]
    assert result.not_collectible_invoice_ids == ["jun"]
    assert result.review_required_invoice_ids == ["jul"]
    assert result.case_collectibility_status is CollectibilityStatus.COLLECTIBLE


def test_unknown_amount_excluded_from_economic_value():
    result = evaluate_collectibility_for_invoices(
        [
            _subject("known", delivery=ServiceDeliveryStatus.DELIVERED, amount=70300),
            _subject("unknown", delivery=ServiceDeliveryStatus.UNKNOWN, amount=70300),
        ]
    )
    assert result.collectible_amount_paise == 70300
    assert result.review_required_amount_paise == 70300
    assert "unknown" not in result.collectible_invoice_ids


def test_integer_paise_preserved_on_gated_result():
    result = evaluate_collectibility_for_invoices(
        [
            _subject("a", amount=499900, delivery=ServiceDeliveryStatus.DELIVERED),
            _subject("b", amount=499900, delivery=ServiceDeliveryStatus.SUSPENDED),
        ]
    )
    assert type(result.historical_unpaid_amount_paise) is int
    assert type(result.collectible_amount_paise) is int
    assert type(result.not_collectible_amount_paise) is int
    assert result.historical_unpaid_amount_paise == 999800
    assert result.collectible_amount_paise == 499900


def test_invoice_payload_missing_delivery_defaults_unknown():
    payload = InvoiceCreatedPayload(
        invoice_id="inv_1",
        billing_cycle="2026-05",
        period_start=T0,
        period_end=T0,
        amount_paise=500000,
    )
    assert payload.service_delivery_status is ServiceDeliveryStatus.UNKNOWN


def test_invoice_payload_rejects_unknown_fields():
    with pytest.raises(ValidationError):
        InvoiceCreatedPayload(
            invoice_id="inv_1",
            billing_cycle="2026-05",
            period_start=T0,
            period_end=T0,
            amount_paise=500000,
            netflix_mode="suspend",
        )


def _case(**kw) -> RecoveryCase:
    defaults = dict(
        case_id="case_1",
        run_id="run_1",
        subscription_id="sub_1",
        customer_id="cust_1",
        halt_episode_id="he_1",
        status=RecoveryCaseStatus.OPEN,
        invoice_ids=["inv_1"],
        invoice_count=1,
        backlog_amount_paise=500000,
        oldest_invoice_at=T0,
        newest_invoice_at=T0,
        halted_at=T0,
        reactivated_at=T0,
        halt_duration_days=30,
        card_type=CardType.DOMESTIC,
        policy_version="v1",
        created_at=T0,
        updated_at=T0,
    )
    defaults.update(kw)
    return RecoveryCase(**defaults)


def test_recovery_case_defaults_collectible_from_backlog():
    case = _case()
    assert case.backlog_amount_paise == case.collectible_amount_paise == 500000
    assert case.collectible_invoice_ids == ["inv_1"]
    assert case.is_strategy_eligible() is True


def test_recovery_case_rejects_mismatched_backlog_and_collectible():
    with pytest.raises(ValidationError, match="backlog_amount_paise must equal"):
        _case(collectible_amount_paise=1)


def test_review_required_case_is_not_strategy_eligible():
    case = _case(
        status=RecoveryCaseStatus.REVIEW_REQUIRED,
        collectibility_status=CollectibilityStatus.REVIEW_REQUIRED,
        invoice_ids=[],
        invoice_count=0,
        backlog_amount_paise=0,
        collectible_amount_paise=0,
        historical_unpaid_amount_paise=1500000,
        review_required_amount_paise=1500000,
        collectible_invoice_ids=[],
        review_required_invoice_ids=["a", "b", "c"],
    )
    assert case.backlog_amount_paise == case.collectible_amount_paise == 0
    assert case.is_strategy_eligible() is False
    assert case.evaluated_invoice_ids() == ["a", "b", "c"]
