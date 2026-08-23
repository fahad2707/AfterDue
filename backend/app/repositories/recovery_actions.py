from pymongo.errors import DuplicateKeyError

from app.models.agent import RecoveryAction
from app.repositories.base import Repository, strip_id


class RecoveryActionRepository(Repository):
    @property
    def col(self):
        return self.db["recovery_actions"]

    async def create_if_absent(self, action: RecoveryAction) -> tuple[RecoveryAction, bool]:
        try:
            await self.col.insert_one(action.model_dump())
            return action, True
        except DuplicateKeyError:
            existing = await self.get_by_key(action.idempotency_key)
            if existing is None:
                raise
            return existing, False

    async def get(self, action_id: str) -> RecoveryAction | None:
        doc = strip_id(await self.col.find_one({"action_id": action_id}))
        return RecoveryAction.model_validate(doc) if doc else None

    async def get_by_key(self, idempotency_key: str) -> RecoveryAction | None:
        doc = strip_id(await self.col.find_one({"idempotency_key": idempotency_key}))
        return RecoveryAction.model_validate(doc) if doc else None

    async def list_for_agent(self, agent_run_id: str) -> list[RecoveryAction]:
        cursor = self.col.find({"agent_run_id": agent_run_id}).sort([("attempt_number", 1)])
        return [RecoveryAction.model_validate(strip_id(d)) async for d in cursor]

    async def save(self, action: RecoveryAction) -> None:
        await self.col.replace_one({"action_id": action.action_id}, action.model_dump())
