from datetime import datetime

from pymongo import ReturnDocument
from pymongo.errors import DuplicateKeyError

from app.domain.enums import RecoveryCaseStatus
from app.models.documents import RecoveryCase
from app.repositories.base import Repository, strip_id


class RecoveryCaseRepository(Repository):
    @property
    def col(self):
        return self.db["recovery_cases"]

    async def create_if_absent(self, case: RecoveryCase) -> tuple[RecoveryCase, bool]:
        """Insert the case, or return the one that already owns this episode.

        The unique index on (subscription_id, halt_episode_id) is the mutex.
        Two reactivation workers both insert; exactly one wins. This is the
        same shape as event claiming — check-then-insert is not used.
        """
        try:
            await self.col.insert_one(case.model_dump())
            return case, True
        except DuplicateKeyError:
            existing = await self.get_by_episode(
                case.subscription_id, case.halt_episode_id
            )
            if existing is None:
                existing = await self.get(case.case_id)
            if existing is None:
                raise
            return existing, False

    async def get(self, case_id: str) -> RecoveryCase | None:
        doc = strip_id(await self.col.find_one({"case_id": case_id}))
        return RecoveryCase.model_validate(doc) if doc else None

    async def get_by_episode(
        self, subscription_id: str, halt_episode_id: str
    ) -> RecoveryCase | None:
        doc = strip_id(
            await self.col.find_one(
                {
                    "subscription_id": subscription_id,
                    "halt_episode_id": halt_episode_id,
                }
            )
        )
        return RecoveryCase.model_validate(doc) if doc else None

    async def list_by_run(
        self, run_id: str, status: RecoveryCaseStatus | None = None
    ) -> list[RecoveryCase]:
        query: dict = {"run_id": run_id}
        if status is not None:
            query["status"] = status.value
        cursor = self.col.find(query).sort([("backlog_amount_paise", -1)])
        return [RecoveryCase.model_validate(strip_id(d)) async for d in cursor]

    async def set_synthetic_identity(
        self,
        case_id: str,
        *,
        synthetic_case_key: str,
        synthetic_customer_key: str,
    ) -> None:
        await self.col.update_one(
            {"case_id": case_id},
            {
                "$set": {
                    "synthetic_case_key": synthetic_case_key,
                    "synthetic_customer_key": synthetic_customer_key,
                }
            },
        )

    async def update_status(
        self, case_id: str, status: RecoveryCaseStatus, now: datetime
    ) -> RecoveryCase | None:
        doc = await self.col.find_one_and_update(
            {"case_id": case_id},
            {"$set": {"status": status.value, "updated_at": now}},
            return_document=ReturnDocument.AFTER,
        )
        return RecoveryCase.model_validate(strip_id(doc)) if doc else None

    async def record_attempt(
        self, case_id: str, *, now: datetime, contacted: bool
    ) -> RecoveryCase | None:
        update: dict = {"$inc": {"attempt_count": 1}, "$set": {"updated_at": now}}
        if contacted:
            update["$set"]["last_contact_at"] = now
        doc = await self.col.find_one_and_update(
            {"case_id": case_id},
            update,
            return_document=ReturnDocument.AFTER,
        )
        return RecoveryCase.model_validate(strip_id(doc)) if doc else None

    async def close_recovered(
        self, case_id: str, *, amount_recovered_paise: int, now: datetime
    ) -> RecoveryCase | None:
        doc = await self.col.find_one_and_update(
            {"case_id": case_id},
            {
                "$set": {
                    "status": RecoveryCaseStatus.CLOSED.value,
                    "amount_recovered_paise": amount_recovered_paise,
                    "updated_at": now,
                }
            },
            return_document=ReturnDocument.AFTER,
        )
        return RecoveryCase.model_validate(strip_id(doc)) if doc else None
