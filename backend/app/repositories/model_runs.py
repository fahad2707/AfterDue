from pymongo import DESCENDING

from app.models.model_run import ModelRun
from app.repositories.base import Repository, strip_id


class ModelRunRepository(Repository):
    @property
    def col(self):
        return self.db["model_runs"]

    async def insert(self, run: ModelRun) -> None:
        if run.is_active:
            await self.col.update_many({"is_active": True}, {"$set": {"is_active": False}})
        await self.col.insert_one(run.model_dump())

    async def get_active(self) -> ModelRun | None:
        doc = strip_id(await self.col.find_one({"is_active": True}))
        return ModelRun.model_validate(doc) if doc else None

    async def get(self, model_run_id: str) -> ModelRun | None:
        doc = strip_id(await self.col.find_one({"model_run_id": model_run_id}))
        return ModelRun.model_validate(doc) if doc else None

    async def list_recent(self, limit: int = 20) -> list[ModelRun]:
        cursor = self.col.find({}).sort([("trained_at", DESCENDING)]).limit(limit)
        return [ModelRun.model_validate(strip_id(d)) async for d in cursor]
