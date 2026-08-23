"""Atomic intervention-slot claims. Two workers cannot take the last slot."""

from pymongo import ReturnDocument

from app.repositories.base import Repository


class BudgetRepository(Repository):
    @property
    def col(self):
        return self.db["intervention_budgets"]

    async def ensure(self, run_id: str, limit: int) -> None:
        await self.col.update_one(
            {"run_id": run_id},
            {"$setOnInsert": {"run_id": run_id, "claimed": 0, "limit": limit}},
            upsert=True,
        )

    async def remaining(self, run_id: str, limit: int) -> int:
        await self.ensure(run_id, limit)
        doc = await self.col.find_one({"run_id": run_id})
        if doc is None:
            return limit
        return max(0, int(doc.get("limit", limit)) - int(doc.get("claimed", 0)))

    async def claim(self, run_id: str, limit: int) -> bool:
        await self.ensure(run_id, limit)
        doc = await self.col.find_one_and_update(
            {"run_id": run_id, "$expr": {"$lt": ["$claimed", "$limit"]}},
            {"$inc": {"claimed": 1}},
            return_document=ReturnDocument.AFTER,
        )
        return doc is not None
