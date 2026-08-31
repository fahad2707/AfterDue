"""Scenario families for evaluation reporting.

Tags are labels on already-generated cases. They do not change sampling
weights and are not shown to strategies.
"""

from app.domain.enums import ActionType
from app.simulator.costs import consumes_budget
from app.simulator.oracle import recovery_probability
from app.simulator.strategies import CaseView

# Family ids are stable keys used by the UI.
FULLY_COLLECTIBLE = "fully_collectible"
PARTIALLY_COLLECTIBLE = "partially_collectible"
SUSPENDED_SERVICE = "suspended_service"
REVIEW_REQUIRED = "review_required"
HIGH_VALUE_LOW_PROB = "high_value_low_probability"
LOW_VALUE_HIGH_PROB = "low_value_high_probability"
POLICY_BLOCKED = "policy_blocked"
SELF_CURE = "likely_self_cure"
INTERVENTION_HELPS = "intervention_improves_recovery"
UNLIKELY = "unlikely_regardless"


def tag_families(
    *,
    collectible: int,
    historical: int,
    excluded: int,
    review: int,
    gated: CaseView | None,
    ungated: CaseView,
    latent: float,
    historical_success: float,
    has_dispute: bool,
    opted_out: bool,
) -> tuple[str, ...]:
    tags: list[str] = []
    if collectible == historical and collectible > 0:
        tags.append(FULLY_COLLECTIBLE)
    if collectible > 0 and (excluded > 0 or review > 0):
        tags.append(PARTIALLY_COLLECTIBLE)
    if excluded > 0 and collectible == 0 and review == 0:
        tags.append(SUSPENDED_SERVICE)
    if review > 0 and collectible == 0:
        tags.append(REVIEW_REQUIRED)

    view = gated or ungated
    automated = [a for a in view.allowed_actions if consumes_budget(a)]
    if view.stop or not automated:
        tags.append(POLICY_BLOCKED)

    p_no = recovery_probability(
        ActionType.NO_ACTION,
        latent=latent,
        historical_success=historical_success,
        has_dispute=has_dispute,
        opted_out=opted_out,
    )
    p_link = recovery_probability(
        ActionType.SEND_PAYMENT_LINK,
        latent=latent,
        historical_success=historical_success,
        has_dispute=has_dispute,
        opted_out=opted_out,
    )
    p_charge = recovery_probability(
        ActionType.ATTEMPT_MANUAL_CHARGE,
        latent=latent,
        historical_success=historical_success,
        has_dispute=has_dispute,
        opted_out=opted_out,
    )
    # Thresholds are reporting cut-points, not strategy features.
    if collectible >= 500_000 and max(p_link, p_charge) < 0.30:
        tags.append(HIGH_VALUE_LOW_PROB)
    if 0 < collectible <= 199_900 and max(p_link, p_charge) >= 0.55:
        tags.append(LOW_VALUE_HIGH_PROB)
    if p_no >= 0.28:
        tags.append(SELF_CURE)
    if max(p_link, p_charge) - p_no >= 0.18:
        tags.append(INTERVENTION_HELPS)
    if max(p_link, p_charge) < 0.16:
        tags.append(UNLIKELY)
    return tuple(tags)


FAMILY_LABELS = {
    FULLY_COLLECTIBLE: "Fully collectible historical debt",
    PARTIALLY_COLLECTIBLE: "Partially collectible debt",
    SUSPENDED_SERVICE: "Suspended-service invoices",
    REVIEW_REQUIRED: "Ambiguous service delivery (review)",
    HIGH_VALUE_LOW_PROB: "High-value / low-probability",
    LOW_VALUE_HIGH_PROB: "Low-value / high-probability",
    POLICY_BLOCKED: "Policy-blocked automated actions",
    SELF_CURE: "Likely to self-cure",
    INTERVENTION_HELPS: "Intervention materially improves recovery",
    UNLIKELY: "Unlikely to recover regardless",
}
