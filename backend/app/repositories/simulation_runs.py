from pymongo import DESCENDING
from pymongo.errors import DuplicateKeyError

from app.models.simulation import SimulationRun, SimulationStatus
from app.repositories.base import Repository, strip_id


class SimulationRunRepository(Repository):
    @property
    def col(self):
        return self.db["simulation_runs"]

    async def create(self, run: SimulationRun) -> bool:
        try:
            await self.col.insert_one(run.model_dump())
            return True
        except DuplicateKeyError:
            return False

    async def get(self, run_id: str) -> SimulationRun | None:
        doc = strip_id(await self.col.find_one({"run_id": run_id}))
        return SimulationRun.model_validate(doc) if doc else None

    async def list_recent(self, limit: int = 50) -> list[SimulationRun]:
        cursor = self.col.find({}).sort([("created_at", DESCENDING)]).limit(limit)
        return [SimulationRun.model_validate(strip_id(d)) async for d in cursor]

    async def save(self, run: SimulationRun) -> None:
        await self.col.replace_one({"run_id": run.run_id}, run.model_dump())

    async def mark(
        self,
        run_id: str,
        status: SimulationStatus,
        **fields,
    ) -> SimulationRun | None:
        update = {"status": status.value, **fields}
        await self.col.update_one({"run_id": run_id}, {"$set": update})
        return await self.get(run_id)
