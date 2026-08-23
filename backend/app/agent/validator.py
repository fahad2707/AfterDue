"""Execution-time validator. Re-evaluates policy immediately before acting."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

from app.config import get_settings
from app.domain.enums import ActionType, PolicyReasonCode, RecoveryCaseStatus, StopReason
from app.domain.policy import PolicyContext, PolicyDecision
from app.models.documents import Customer, RecoveryCase, Subscription
from app.policy import evaluate_v1
from app.simulator.costs import consumes_budget
from app.simulator.world import DECISION_NOW


@dataclass(frozen=True)
class ValidationResult:
    ok: bool
    action: ActionType
    stop_reason: StopReason | None
    escalate: bool
    next_eligible_at: datetime | None
    planning_decision: PolicyDecision
    execution_decision: PolicyDecision


class ActionValidator:
    def validate(
        self,
        *,
        case: RecoveryCase,
        customer: Customer,
        subscription: Subscription,
        action: ActionType,
        planning_decision: PolicyDecision,
        budget_remaining: int,
        now: datetime | None = None,
        existing_action: bool = False,
    ) -> ValidationResult:
        settings = get_settings()
        moment = now or DECISION_NOW
        execution = evaluate_v1(
            PolicyContext(
                case_id=case.case_id,
                card_type=subscription.card_type,
                backlog_amount_paise=case.backlog_amount_paise,
                mandate_max_amount_paise=subscription.mandate_max_amount_paise,
                risk_flags=customer.risk_flags,
                has_dispute=customer.has_active_dispute,
                customer_opted_out=customer.customer_opted_out,
                attempt_count=case.attempt_count,
                last_contact_at=case.last_contact_at,
                now=moment,
                max_attempts=settings.max_recovery_attempts,
                contact_cooldown_hours=settings.policy_contact_cooldown_hours,
            )
        )

        def fail(reason: StopReason, escalate: bool = False, next_at=None) -> ValidationResult:
            return ValidationResult(
                ok=False,
                action=action,
                stop_reason=reason,
                escalate=escalate or execution.requires_escalation,
                next_eligible_at=next_at,
                planning_decision=planning_decision,
                execution_decision=execution,
            )

        if existing_action:
            return fail(StopReason.ALREADY_EXECUTED)
        if case.status is not RecoveryCaseStatus.OPEN:
            return fail(StopReason.CASE_CLOSED)
        if customer.has_active_dispute:
            return fail(StopReason.ACTIVE_DISPUTE, escalate=True)
        if customer.customer_opted_out and action == ActionType.SEND_PAYMENT_LINK:
            return fail(
                StopReason.CUSTOMER_OPTED_OUT,
                escalate=execution.requires_escalation,
            )
        if case.attempt_count >= settings.max_recovery_attempts:
            return fail(StopReason.MAX_ATTEMPTS_REACHED)
        if action not in execution.allowed_actions:
            codes = set(execution.reason_codes)
            if PolicyReasonCode.CUSTOMER_OPTED_OUT in codes:
                return fail(StopReason.CUSTOMER_OPTED_OUT, escalate=True)
            if PolicyReasonCode.ACTIVE_DISPUTE in codes:
                return fail(StopReason.ACTIVE_DISPUTE, escalate=True)
            return fail(
                StopReason.POLICY_BLOCKED,
                escalate=execution.requires_escalation,
            )
        if action is ActionType.SEND_PAYMENT_LINK and case.last_contact_at is not None:
            next_at = case.last_contact_at + timedelta(
                hours=settings.policy_contact_cooldown_hours
            )
            if moment < next_at:
                return fail(StopReason.CONTACT_COOLDOWN_ACTIVE, next_at=next_at)
        if consumes_budget(action) and budget_remaining <= 0:
            return fail(StopReason.BUDGET_EXHAUSTED)
        return ValidationResult(
            ok=True,
            action=action,
            stop_reason=None,
            escalate=False,
            next_eligible_at=None,
            planning_decision=planning_decision,
            execution_decision=execution,
        )
