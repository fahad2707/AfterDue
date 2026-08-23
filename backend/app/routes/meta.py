from fastapi import APIRouter
from pydantic import BaseModel

from app.config import get_settings

router = APIRouter(prefix="/api", tags=["meta"])


class MetaResponse(BaseModel):
    service: str
    app_env: str
    policy_version: str
    llm_enabled: bool
    synthetic: bool


@router.get("/meta", response_model=MetaResponse)
async def meta() -> MetaResponse:
    """Round-trip target for the frontend proxy, and the source of the
    SYNTHETIC badge the UI renders on every surface."""
    settings = get_settings()
    return MetaResponse(
        service="reclaim-backend",
        app_env=settings.app_env,
        policy_version=settings.policy_version,
        llm_enabled=settings.llm_enabled,
        synthetic=True,
    )
