from fastapi import APIRouter

from app.config import get_settings
from app.domain.enums import ActionType, PolicyReasonCode, Provenance
from app.domain.policy import POLICY_VERSION, PolicyDecision
from app.policy import evaluate_v1
from app.policy.rules_v1 import RULE_CATALOG
from app.schemas.recovery import PolicyConfigOut, PolicyEvaluateIn

router = APIRouter(prefix="/api/policy", tags=["policy"])


@router.get("/config", response_model=PolicyConfigOut)
async def policy_config() -> PolicyConfigOut:
    settings = get_settings()
    return PolicyConfigOut(
        policy_version=settings.policy_version or POLICY_VERSION,
        max_attempts=settings.policy_max_attempts,
        contact_cooldown_hours=settings.policy_contact_cooldown_hours,
        actions=[a.value for a in ActionType],
        rules=list(RULE_CATALOG),
        reason_codes=[c.value for c in PolicyReasonCode],
        provenance_values=[p.value for p in Provenance],
    )


@router.post("/evaluate", response_model=PolicyDecision)
async def policy_evaluate(body: PolicyEvaluateIn) -> PolicyDecision:
    """Dry-run. No database write, no action execution."""
    return evaluate_v1(body)
