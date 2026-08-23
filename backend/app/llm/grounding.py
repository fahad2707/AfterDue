"""Reject language output that invents policy, money guarantees, or hidden state."""

from app.llm.schemas import CaseExplanation, ExtractionProposal

FORBIDDEN_CLAIM_TOKENS = (
    "guaranteed recovery",
    "latent_payment_intent",
    "oracle",
    "causal truth",
    "real money",
)


def explanation_is_grounded(explanation: CaseExplanation, facts: dict) -> bool:
    blob = " ".join(
        [
            explanation.summary,
            explanation.why_case_exists,
            explanation.recommended_action_explanation,
            explanation.economic_reasoning,
            *explanation.policy_constraints,
        ]
    ).lower()
    if any(token in blob for token in FORBIDDEN_CLAIM_TOKENS):
        return False
    allowed_codes = {str(c).lower() for c in facts.get("reason_codes") or []}
    for constraint in explanation.policy_constraints:
        for token in constraint.replace("-", "_").split():
            if token.isupper() and "_" in token and token.lower() not in allowed_codes:
                if token.endswith("_UNSUPPORTED") or token.endswith("_EXCEEDED"):
                    return False
    return True


def extraction_is_supported(proposal: ExtractionProposal, source_text: str) -> bool:
    source = source_text.lower()
    needed: list[str] = []
    if proposal.has_dispute is True:
        needed.append("has_dispute")
    if proposal.customer_opted_out is True:
        needed.append("customer_opted_out")
    for field in needed:
        evidence = [e for e in proposal.evidence if e.field == field]
        if not evidence:
            return False
        if not any(e.span and e.span.lower() in source for e in evidence):
            return False
    for item in proposal.evidence:
        if item.span and item.span.lower() not in source:
            return False
    return True
