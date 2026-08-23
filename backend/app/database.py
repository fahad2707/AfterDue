from __future__ import annotations

from pymongo import AsyncMongoClient
from pymongo.asynchronous.database import AsyncDatabase

from app.config import get_settings
from app.logging import get_logger

log = get_logger(__name__)


class MongoConnection:
    """Holds the process-wide Mongo client.

    Every collection access in RECLAIM goes through a repository module; this
    class is the single place that owns the client lifecycle.
    """

    def __init__(self) -> None:
        self._client: AsyncMongoClient | None = None
        self._db: AsyncDatabase | None = None

    async def connect(self) -> None:
        settings = get_settings()
        if not settings.mongodb_uri:
            log.warning("mongo_uri_missing", detail="MONGODB_URI is empty; /readyz will fail")
            return

        self._client = AsyncMongoClient(
            settings.mongodb_uri,
            serverSelectionTimeoutMS=5000,
            connectTimeoutMS=5000,
            tz_aware=True,
            appname="reclaim-backend",
        )
        self._db = self._client[settings.mongodb_db]
        log.info("mongo_client_created", database=settings.mongodb_db)

    async def close(self) -> None:
        if self._client is not None:
            await self._client.close()
            self._client = None
            self._db = None
            log.info("mongo_client_closed")

    @property
    def db(self) -> AsyncDatabase:
        if self._db is None:
            raise RuntimeError("MongoDB is not connected")
        return self._db

    async def ping(self) -> tuple[bool, str | None]:
        """Return (ok, error). Never raises — /readyz turns this into a status."""
        if self._client is None:
            return False, "client_not_initialised"
        try:
            await self._client.admin.command("ping")
            return True, None
        except Exception as exc:  # noqa: BLE001 - readiness must not raise
            return False, f"{type(exc).__name__}: {exc}"


mongo = MongoConnection()
