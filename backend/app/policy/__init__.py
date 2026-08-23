from app.domain.policy import POLICY_VERSION, PolicyContext, PolicyDecision, evaluate_policy
from app.policy.rules_v1 import RULES_V1


def evaluate_v1(context: PolicyContext) -> PolicyDecision:
    return evaluate_policy(context, RULES_V1, version=POLICY_VERSION)


__all__ = [
    "POLICY_VERSION",
    "PolicyContext",
    "PolicyDecision",
    "RULES_V1",
    "evaluate_policy",
    "evaluate_v1",
]
