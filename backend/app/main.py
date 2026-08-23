from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import get_settings
from app.database import mongo
from app.logging import configure_logging, get_logger
from app.repositories.indexes import ensure_indexes
from app.routes import events, health, ledger, meta

settings = get_settings()
configure_logging(level=settings.log_level, json_output=settings.app_env != "local")
log = get_logger("reclaim.api")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    log.info("startup_begin", app_env=settings.app_env)
    await mongo.connect()
    ok, err = await mongo.ping()
    log.info("startup_mongo_check", ok=ok, detail=err)
    if ok:
        # Idempotent, and several of these indexes are correctness constraints
        # rather than optimisations, so the app must not serve without them.
        await ensure_indexes(mongo.db)
    yield
    await mongo.close()
    log.info("shutdown_complete")


app = FastAPI(
    title="RECLAIM API",
    description="Post-halt subscription revenue recovery agent. Synthetic data only.",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def require_internal_key(request: Request, call_next):
    """Only the Next.js server-side proxy may call /api/*.

    The browser never holds this key, so the frontend cannot reach an endpoint
    the proxy does not deliberately expose. Disabled when the key is unset so
    that a fresh clone runs without configuration.

    Returns a response rather than raising: HTTP middleware sits outside the
    exception-handling middleware, so a raised HTTPException escapes as a 500.

    Reads settings per request rather than closing over an import-time value,
    so the key can be changed without reimporting the module.
    """
    key = get_settings().internal_api_key
    if key and request.url.path.startswith("/api"):
        if request.headers.get("x-internal-api-key") != key:
            log.warning("internal_key_rejected", path=request.url.path)
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={"detail": "invalid internal api key"},
            )
    return await call_next(request)


app.include_router(health.router)
app.include_router(meta.router)
app.include_router(events.router)
app.include_router(ledger.router)
