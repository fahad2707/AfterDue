"""Structured fact pack the language layer is allowed to see. No oracle."""

from __future__ import annotations

from app.domain.money import format_paise
from app.domain.policy import PolicyDecision
from app.models.documents import RecoveryCase


def explanation_facts(
    case: RecoveryCase,
    policy: PolicyDecision,
    analysis: dict | None,
) -> dict:
    recommended = (
        analysis.get("selected_action")
        if analysis
        else (policy.allowed_actions[0].value if policy.allowed_actions else "no_action")
    )
    return {
        "backlog_amount_paise": case.backlog_amount_paise,
        "backlog_display": format_paise(case.backlog_amount_paise),
        "collectible_amount_paise": case.collectible_amount_paise,
        "historical_unpaid_amount_paise": case.historical_unpaid_amount_paise,
        "review_required_amount_paise": case.review_required_amount_paise,
        "not_collectible_amount_paise": case.not_collectible_amount_paise,
        "invoice_count": case.invoice_count,
        "halt_duration_days": case.halt_duration_days,
        "reactivated": True,
        "case_status": case.status.value,
        "allowed_actions": [a.value for a in policy.allowed_actions],
        "blocked_actions": [a.value for a in policy.blocked_actions],
        "reason_codes": [c.value for c in policy.reason_codes],
        "p_no_action": analysis.get("p_no_action") if analysis else None,
        "p_selected_action": analysis.get("p_selected_action") if analysis else None,
        "estimated_uplift": analysis.get("estimated_uplift") if analysis else None,
        "expected_incremental_recovery_paise": (
            analysis.get("expected_incremental_recovery_paise") if analysis else None
        ),
        "recommended_action": recommended,
        "model_version": analysis.get("model_version") if analysis else None,
        "policy_version": policy.policy_version,
        "synthetic": True,
    }


def qa_facts(
    case: RecoveryCase,
    policy: PolicyDecision,
    analysis: dict | None,
    audit: list,
) -> dict:
    pack = explanation_facts(case, policy, analysis)
    pack["audit"] = [
        {
            "audit_id": entry.audit_id,
            "event_type": entry.event_type.value
            if hasattr(entry.event_type, "value")
            else str(entry.event_type),
            "details": entry.details,
        }
        for entry in audit
    ]
    pack["attempt_count"] = case.attempt_count
    pack["amount_recovered_paise"] = case.amount_recovered_paise
    return pack
