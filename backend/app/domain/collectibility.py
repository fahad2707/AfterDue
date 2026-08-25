"""Deterministic collectibility / service-entitlement gate.

Invoice existence is not proof of collectibility. This module decides whether
an unpaid halt-period invoice is a valid receivable before any recovery case
enters policy, ML, or the agent.

Pure: no I/O, no clock, no ML, no LLM, no oracle.
"""

from collections.abc import Sequence
from dataclasses import dataclass

from app.domain.enums import (
    CollectibilityReasonCode,
    CollectibilityStatus,
    InvoiceStatus,
    ServiceDeliveryStatus,
)


@dataclass(frozen=True)
class CollectibilitySubject:
    """Minimum facts the engine needs. Persistence shapes stay out of the rules."""

    invoice_id: str
    status: InvoiceStatus
    amount_paise: int
    service_delivery_status: ServiceDeliveryStatus = ServiceDeliveryStatus.UNKNOWN
    waived: bool = False
    merchant_marked_non_collectible: bool = False


@dataclass(frozen=True)
class CollectibilityDecision:
    invoice_id: str
    status: CollectibilityStatus
    reason_codes: tuple[CollectibilityReasonCode, ...]
    eligible_amount_paise: int

    @property
    def is_collectible(self) -> bool:
        return self.status is CollectibilityStatus.COLLECTIBLE


@dataclass(frozen=True)
class CollectibleBacklogResult:
    """Gated view of a historical unpaid invoice set.

    `historical_unpaid_amount_paise` is raw halt-lineage unpaid value.
    Only `collectible_amount_paise` may enter recovery economics.
    """

    historical_unpaid_amount_paise: int
    collectible_amount_paise: int
    not_collectible_amount_paise: int
    review_required_amount_paise: int
    historical_unpaid_invoice_ids: list[str]
    collectible_invoice_ids: list[str]
    not_collectible_invoice_ids: list[str]
    review_required_invoice_ids: list[str]
    decisions: tuple[CollectibilityDecision, ...]

    def __post_init__(self) -> None:
        total = (
            self.collectible_amount_paise
            + self.not_collectible_amount_paise
            + self.review_required_amount_paise
        )
        if total != self.historical_unpaid_amount_paise:
            raise ValueError(
                "collectibility buckets must sum to historical unpaid: "
                f"{total} != {self.historical_unpaid_amount_paise}"
            )
        for value in (
            self.historical_unpaid_amount_paise,
            self.collectible_amount_paise,
            self.not_collectible_amount_paise,
            self.review_required_amount_paise,
        ):
            if type(value) is not int:
                raise TypeError("collectibility amounts must be integer paise")

    @property
    def case_collectibility_status(self) -> CollectibilityStatus:
        if self.collectible_amount_paise > 0:
            return CollectibilityStatus.COLLECTIBLE
        if self.review_required_amount_paise > 0:
            return CollectibilityStatus.REVIEW_REQUIRED
        return CollectibilityStatus.NOT_COLLECTIBLE


def subject_from_invoice(invoice) -> CollectibilitySubject:
    """Adapt a persisted Invoice (or any object with the same attributes)."""
    delivery = getattr(invoice, "service_delivery_status", None)
    if delivery is None:
        delivery = ServiceDeliveryStatus.UNKNOWN
    return CollectibilitySubject(
        invoice_id=invoice.invoice_id,
        status=invoice.status,
        amount_paise=int(invoice.amount_paise),
        service_delivery_status=delivery,
        waived=bool(getattr(invoice, "waived", False)),
        merchant_marked_non_collectible=bool(
            getattr(invoice, "merchant_marked_non_collectible", False)
        ),
    )


def evaluate_collectibility(subject: CollectibilitySubject) -> CollectibilityDecision:
    """v1 conservative rules. UNKNOWN and PARTIALLY_DELIVERED fail closed."""
    amount = int(subject.amount_paise)
    if type(subject.amount_paise) is not int:
        raise TypeError("amount_paise must be integer paise")

    # RULE A: paid / non-unpaid invoices never contribute recovery value.
    if subject.status is not InvoiceStatus.ISSUED_UNPAID:
        reason = (
            CollectibilityReasonCode.INVOICE_ALREADY_PAID
            if subject.status is InvoiceStatus.PAID
            else CollectibilityReasonCode.INVOICE_ALREADY_PAID
        )
        return CollectibilityDecision(
            invoice_id=subject.invoice_id,
            status=CollectibilityStatus.NOT_COLLECTIBLE,
            reason_codes=(reason,),
            eligible_amount_paise=0,
        )

    # RULE F: explicit merchant non-collectible / waived flags.
    if subject.waived:
        return CollectibilityDecision(
            invoice_id=subject.invoice_id,
            status=CollectibilityStatus.NOT_COLLECTIBLE,
            reason_codes=(CollectibilityReasonCode.INVOICE_WAIVED,),
            eligible_amount_paise=0,
        )
    if subject.merchant_marked_non_collectible:
        return CollectibilityDecision(
            invoice_id=subject.invoice_id,
            status=CollectibilityStatus.NOT_COLLECTIBLE,
            reason_codes=(CollectibilityReasonCode.MERCHANT_MARKED_NON_COLLECTIBLE,),
            eligible_amount_paise=0,
        )

    delivery = subject.service_delivery_status

    # RULE C
    if delivery is ServiceDeliveryStatus.SUSPENDED:
        return CollectibilityDecision(
            invoice_id=subject.invoice_id,
            status=CollectibilityStatus.NOT_COLLECTIBLE,
            reason_codes=(CollectibilityReasonCode.SERVICE_SUSPENDED,),
            eligible_amount_paise=0,
        )

    # RULE D — UNKNOWN fails closed. Never default to COLLECTIBLE.
    if delivery is ServiceDeliveryStatus.UNKNOWN:
        return CollectibilityDecision(
            invoice_id=subject.invoice_id,
            status=CollectibilityStatus.REVIEW_REQUIRED,
            reason_codes=(CollectibilityReasonCode.SERVICE_DELIVERY_UNKNOWN,),
            eligible_amount_paise=0,
        )

    # RULE E — no proportional split in v1.
    if delivery is ServiceDeliveryStatus.PARTIALLY_DELIVERED:
        return CollectibilityDecision(
            invoice_id=subject.invoice_id,
            status=CollectibilityStatus.REVIEW_REQUIRED,
            reason_codes=(CollectibilityReasonCode.SERVICE_PARTIALLY_DELIVERED,),
            eligible_amount_paise=0,
        )

    # RULE B
    if delivery is ServiceDeliveryStatus.DELIVERED:
        return CollectibilityDecision(
            invoice_id=subject.invoice_id,
            status=CollectibilityStatus.COLLECTIBLE,
            reason_codes=(CollectibilityReasonCode.SERVICE_DELIVERED,),
            eligible_amount_paise=amount,
        )

    return CollectibilityDecision(
        invoice_id=subject.invoice_id,
        status=CollectibilityStatus.REVIEW_REQUIRED,
        reason_codes=(CollectibilityReasonCode.SERVICE_DELIVERY_UNKNOWN,),
        eligible_amount_paise=0,
    )


def evaluate_collectibility_for_invoices(
    invoices: Sequence,
) -> CollectibleBacklogResult:
    """Evaluate an already-reconstructed historical unpaid invoice set."""
    decisions: list[CollectibilityDecision] = []
    collectible_ids: list[str] = []
    excluded_ids: list[str] = []
    review_ids: list[str] = []
    collectible = 0
    excluded = 0
    review = 0
    historical = 0
    historical_ids: list[str] = []

    for invoice in invoices:
        subject = (
            invoice
            if isinstance(invoice, CollectibilitySubject)
            else subject_from_invoice(invoice)
        )
        historical += int(subject.amount_paise)
        historical_ids.append(subject.invoice_id)
        decision = evaluate_collectibility(subject)
        decisions.append(decision)
        if decision.status is CollectibilityStatus.COLLECTIBLE:
            collectible += decision.eligible_amount_paise
            collectible_ids.append(decision.invoice_id)
        elif decision.status is CollectibilityStatus.NOT_COLLECTIBLE:
            excluded += int(subject.amount_paise)
            excluded_ids.append(decision.invoice_id)
        else:
            review += int(subject.amount_paise)
            review_ids.append(decision.invoice_id)

    assert isinstance(historical, int)
    assert isinstance(collectible, int)
    assert type(collectible) is int

    return CollectibleBacklogResult(
        historical_unpaid_amount_paise=historical,
        collectible_amount_paise=collectible,
        not_collectible_amount_paise=excluded,
        review_required_amount_paise=review,
        historical_unpaid_invoice_ids=historical_ids,
        collectible_invoice_ids=collectible_ids,
        not_collectible_invoice_ids=excluded_ids,
        review_required_invoice_ids=review_ids,
        decisions=tuple(decisions),
    )
