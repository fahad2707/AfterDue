import time

from fastapi import APIRouter, Response, status
from pydantic import BaseModel

from app.config import get_settings
from app.database import mongo

router = APIRouter(tags=["health"])

_STARTED_AT = time.time()


class HealthResponse(BaseModel):
    status: str
    service: str = "reclaim-backend"
    version: str = "0.1.0"
    app_env: str
    uptime_seconds: float


class DependencyStatus(BaseModel):
    ok: bool
    detail: str | None = None


class ReadyResponse(BaseModel):
    ready: bool
    checks: dict[str, DependencyStatus]


@router.get("/healthz", response_model=HealthResponse)
async def healthz() -> HealthResponse:
    """Liveness. Must not touch dependencies — the process is up or it isn't."""
    settings = get_settings()
    return HealthResponse(
        status="ok",
        app_env=settings.app_env,
        uptime_seconds=round(time.time() - _STARTED_AT, 3),
    )


@router.get("/readyz", response_model=ReadyResponse)
async def readyz(response: Response) -> ReadyResponse:
    """Readiness. Checks every dependency the app needs to serve real traffic.

    Reports the health of the *current connection pool*, not the current
    validity of credentials: the driver authenticates when a connection is
    established, so a pooled connection keeps answering ping after a password
    rotation. A restart surfaces the real state. See docs/incidents.md INC-004.

    The recovery-model artifact is optional for liveness. Missing Mongo
    still fails readiness.
    """
    mongo_ok, mongo_err = await mongo.ping()
    checks = {"mongodb": DependencyStatus(ok=mongo_ok, detail=mongo_err)}

    ready = all(c.ok for c in checks.values())
    if not ready:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return ReadyResponse(ready=ready, checks=checks)
