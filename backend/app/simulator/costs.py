"""Synthetic intervention costs. PRODUCT DESIGN / SIMULATION ASSUMPTIONS.

These are not Razorpay prices. They exist so a later incremental-EV
calculation has a non-zero cost term. Integer paise only.
"""

from app.domain.enums import ActionType

# ₹0 / ₹2 / ₹5 / ₹50 — documented in docs/evaluation.md
ACTION_COST_PAISE: dict[ActionType, int] = {
    ActionType.NO_ACTION: 0,
    ActionType.SEND_PAYMENT_LINK: 200,
    ActionType.ATTEMPT_MANUAL_CHARGE: 500,
    ActionType.ESCALATE_TO_MERCHANT: 5000,
}

BUDGET_CONSUMING: frozenset[ActionType] = frozenset(
    {ActionType.SEND_PAYMENT_LINK, ActionType.ATTEMPT_MANUAL_CHARGE}
)


def cost_of(action: ActionType) -> int:
    return ACTION_COST_PAISE[action]


def consumes_budget(action: ActionType) -> bool:
    """Escalation is operational work, not an automated intervention slot."""
    return action in BUDGET_CONSUMING
