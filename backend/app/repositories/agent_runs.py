from app.models.agent import AgentRun
from app.repositories.base import Repository, strip_id


class AgentRunRepository(Repository):
    @property
    def col(self):
        return self.db["agent_runs"]

    async def insert(self, run: AgentRun) -> None:
        await self.col.insert_one(run.model_dump())

    async def get(self, agent_run_id: str) -> AgentRun | None:
        doc = strip_id(await self.col.find_one({"agent_run_id": agent_run_id}))
        return AgentRun.model_validate(doc) if doc else None

    async def save(self, run: AgentRun) -> None:
        await self.col.replace_one({"agent_run_id": run.agent_run_id}, run.model_dump())
