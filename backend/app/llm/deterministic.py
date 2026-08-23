"""Deterministic language. Works with LLM_ENABLED=false."""

from __future__ import annotations

from app.domain.money import format_paise
from app.llm.schemas import CaseExplanation, ExtractionProposal, QAAnswer

REASON_SENTENCES = {
    "DOMESTIC_CARD_MANUAL_CHARGE_UNSUPPORTED": (
        "Policy blocks manual charging because this subscription uses a domestic card."
    ),
    "MANDATE_CAP_EXCEEDED": (
        "Policy blocks manual charging because the backlog exceeds the mandate cap "
        "used by this prototype."
    ),
    "RISK_FLAG_PRESENT": (
        "Policy blocks automated collection because a risk flag is present."
    ),
    "ACTIVE_DISPUTE": "Policy stops automated recovery because of an active dispute.",
    "CUSTOMER_OPTED_OUT": "Policy blocks payment-link contact because the customer opted out.",
    "MAX_ATTEMPTS_REACHED": "Policy blocks further automated collection: attempt limit reached.",
    "CONTACT_COOLDOWN_ACTIVE": "Policy blocks another payment-link contact during cooldown.",
}


def explain(facts: dict) -> CaseExplanation:
    backlog = format_paise(int(facts["backlog_amount_paise"]))
    invoices = int(facts["invoice_count"])
    action = str(facts.get("recommended_action") or "no_action").replace("_", " ")
    why = (
        f"RECLAIM identified {backlog} across {invoices} unpaid invoice"
        f"{'' if invoices == 1 else 's'} generated during this subscription's "
        "halted period. The subscription has since returned to active."
    )
    constraints = [
        REASON_SENTENCES[code]
        for code in facts.get("reason_codes") or []
        if code in REASON_SENTENCES
    ]
    p_no = facts.get("p_no_action")
    p_sel = facts.get("p_selected_action")
    lift = facts.get("estimated_uplift")
    ev = facts.get("expected_incremental_recovery_paise")
    if p_no is not None and p_sel is not None and lift is not None:
        rec = (
            f"The recovery model estimates that {action} changes model-estimated "
            f"recovery from {p_no:.0%} to {p_sel:.0%}, an estimated intervention "
            f"lift of {lift * 100:.1f} percentage points."
        )
        econ = (
            "Expected incremental recovery is backlog × estimated lift minus the "
            f"synthetic action cost, which is {format_paise(int(ev or 0))}."
            if ev is not None
            else "Expected incremental recovery was not available for this case."
        )
    else:
        rec = f"The recommended action from policy-constrained ranking is {action}."
        econ = "No recovery-model analysis is available; ranking used policy only."
    if facts.get("recommended_action") == "no_action":
        rec += (
            " Doing nothing can be economically better when estimated "
            "incremental value is not positive."
        )
    return CaseExplanation(
        summary=why + " " + rec,
        why_case_exists=why,
        recommended_action_explanation=rec,
        policy_constraints=constraints
        or ["Policy still determines which actions are eligible."],
        economic_reasoning=econ,
        uncertainty_note=(
            "These are model estimates from a synthetic randomized environment, "
            "not guaranteed recovery and not Razorpay production statistics."
        ),
    )


def answer(question: str, facts: dict) -> QAAnswer:
    q = question.lower()
    grounding: list[str] = []
    if "created" in q or "why was this case" in q:
        grounding = ["invoice_count", "backlog_amount_paise", "reactivated"]
        return QAAnswer(
            answer=(
                f"The case exists because the subscription returned to active after a "
                f"halt that left {facts['invoice_count']} unpaid invoices totaling "
                f"{format_paise(int(facts['backlog_amount_paise']))}."
            ),
            grounding=grounding,
        )
    if "manual" in q or "charge" in q:
        codes = facts.get("reason_codes") or []
        blocked = facts.get("blocked_actions") or []
        grounding = ["blocked_actions", "reason_codes"]
        if "attempt_manual_charge" in blocked:
            charge_codes = {
                "DOMESTIC_CARD_MANUAL_CHARGE_UNSUPPORTED",
                "MANDATE_CAP_EXCEEDED",
                "RISK_FLAG_PRESENT",
                "ACTIVE_DISPUTE",
            }
            reasons = [REASON_SENTENCES[c] for c in codes if c in charge_codes]
            return QAAnswer(
                answer=" ".join(reasons)
                or "Manual charge is in the blocked-action set for this case.",
                grounding=grounding,
            )
        return QAAnswer(
            answer="Manual charge is not recorded as blocked on this case.",
            grounding=grounding,
        )
    if "no action" in q or "doing nothing" in q:
        ev = facts.get("expected_incremental_recovery_paise")
        grounding = ["recommended_action", "expected_incremental_recovery_paise"]
        return QAAnswer(
            answer=(
                "RECLAIM selected no action because every automated intervention had "
                f"non-positive expected incremental recovery ({ev} paise) or policy "
                "forbade contact."
                if facts.get("recommended_action") == "no_action"
                else f"The recommended action is {facts.get('recommended_action')}."
            ),
            grounding=grounding,
        )
    if "selected" in q or "payment link" in q or "recommended" in q:
        grounding = [
            "recommended_action",
            "estimated_uplift",
            "expected_incremental_recovery_paise",
        ]
        recommended = str(facts.get("recommended_action")).replace("_", " ")
        return QAAnswer(
            answer=(
                f"The recommended action is {recommended}. "
                "It is the policy-permitted action with the highest positive expected "
                "incremental recovery from the recovery model, or no action if none is positive."
            ),
            grounding=grounding,
        )
    if "incremental" in q or "expected" in q or "calculated" in q or "lift" in q:
        grounding = [
            "backlog_amount_paise",
            "estimated_uplift",
            "expected_incremental_recovery_paise",
        ]
        ev = facts.get("expected_incremental_recovery_paise")
        lift = facts.get("estimated_uplift")
        if ev is None or lift is None:
            return QAAnswer(
                answer="The audit trail does not contain enough information to determine that.",
                grounding=grounding,
                insufficient_information=True,
            )
        return QAAnswer(
            answer=(
                "Expected incremental recovery is backlog_amount_paise × estimated "
                f"intervention lift ({lift:.3f}) minus the synthetic action cost, "
                f"rounded to {ev} paise."
            ),
            grounding=grounding,
        )
    if "policy" in q or "blocked" in q:
        grounding = ["reason_codes", "blocked_actions"]
        codes = ", ".join(facts.get("reason_codes") or []) or "none"
        return QAAnswer(
            answer=f"Policy reason codes on this case: {codes}.",
            grounding=grounding,
        )
    return QAAnswer(
        answer="The audit trail does not contain enough information to determine that.",
        grounding=["audit"],
        insufficient_information=True,
    )


def extract_without_model(source_text: str) -> ExtractionProposal:
    """Conservative keyword extract used when the language layer is off."""
    text = source_text.lower()
    evidence = []
    has_dispute = None
    opted_out = None
    if "dispute" in text:
        has_dispute = True
        start = text.find("dispute")
        evidence.append(
            {"field": "has_dispute", "span": source_text[start : start + 7], "confidence": 0.6}
        )
    if "do not want" in text or "opt out" in text or "opted out" in text or "no further" in text:
        opted_out = True
        for needle in ("do not want", "opt out", "no further"):
            idx = text.find(needle)
            if idx >= 0:
                evidence.append(
                    {
                        "field": "customer_opted_out",
                        "span": source_text[idx : idx + len(needle)],
                        "confidence": 0.6,
                    }
                )
                break
    from app.llm.schemas import ExtractionEvidence

    return ExtractionProposal(
        has_dispute=has_dispute,
        customer_opted_out=opted_out,
        evidence=[ExtractionEvidence(**e) for e in evidence],
        uncertainty_note="Keyword fallback. No Claude call was made.",
    )
