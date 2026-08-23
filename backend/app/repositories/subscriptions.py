from datetime import datetime

from pymongo import ReturnDocument
from pymongo.errors import DuplicateKeyError

from app.domain.enums import SubscriptionStatus
from app.models.documents import HaltEpisode, Subscription
from app.repositories.base import Repository, strip_id


class SubscriptionRepository(Repository):
    @property
    def col(self):
        return self.db["subscriptions"]

    async def create(self, subscription: Subscription) -> bool:
        try:
            await self.col.insert_one(subscription.model_dump())
            return True
        except DuplicateKeyError:
            return False

    async def get(self, subscription_id: str) -> Subscription | None:
        doc = strip_id(await self.col.find_one({"subscription_id": subscription_id}))
        return Subscription.model_validate(doc) if doc else None

    async def list_with_closed_halt_episodes(
        self, run_id: str | None = None
    ) -> list[Subscription]:
        """Subscriptions that have at least one closed halt episode.

        Used by reconciliation. An open episode is not a recovery window —
        the customer has not returned yet. `run_id` keeps repairs inside one
        simulation so run A cannot create cases for run B.
        """
        query: dict = {"halt_episodes.reactivated_at": {"$ne": None}}
        if run_id is not None:
            query["run_id"] = run_id
        cursor = self.col.find(query)
        return [Subscription.model_validate(strip_id(d)) async for d in cursor]

    async def apply_transition(
        self,
        subscription_id: str,
        expected_from: SubscriptionStatus,
        to_status: SubscriptionStatus,
        occurred_at: datetime,
        now: datetime,
        open_episode: HaltEpisode | None = None,
        close_open_episode: bool = False,
    ) -> Subscription | None:
        """Compare-and-swap the subscription status.

        The filter pins the status we believe the subscription is in, so the
        update only lands if nothing changed since we read it. A concurrent
        writer that already moved the status causes this to match nothing and
        return None, which the caller reports as CONCURRENT_MODIFICATION rather
        than overwriting someone else's transition.

        `last_state_change_at` is set to the event's `occurred_at` — logical
        time, not our wall clock — because staleness detection compares
        incoming events against it.
        """
        update: dict = {
            "$set": {
                "status": to_status.value,
                "last_state_change_at": occurred_at,
                "updated_at": now,
            }
        }
        array_filters = None

        if open_episode is not None:
            update["$push"] = {"halt_episodes": open_episode.model_dump()}

        if close_open_episode:
            # Close the single open episode. The state machine guarantees this
            # never coincides with opening one, so there is no path conflict.
            update["$set"]["halt_episodes.$[open].reactivated_at"] = occurred_at
            array_filters = [{"open.reactivated_at": None}]

        doc = await self.col.find_one_and_update(
            {"subscription_id": subscription_id, "status": expected_from.value},
            update,
            array_filters=array_filters,
            return_document=ReturnDocument.AFTER,
        )
        return Subscription.model_validate(strip_id(doc)) if doc else None

    async def attach_invoice_to_episode(
        self, subscription_id: str, episode_id: str, invoice_id: str
    ) -> bool:
        """Record an invoice against a specific halt episode.

        Targets the episode by id rather than "the currently open one" so that
        an invoice event arriving after reactivation still lands on the episode
        whose window contains it.

        `$addToSet` rather than `$push`: replaying the same invoice must not
        add the id twice.
        """
        result = await self.col.update_one(
            {"subscription_id": subscription_id},
            {"$addToSet": {"halt_episodes.$[ep].invoice_ids": invoice_id}},
            array_filters=[{"ep.episode_id": episode_id}],
        )
        return result.modified_count > 0

    async def next_audit_seq(self, subscription_id: str) -> int:
        """Allocate the next audit sequence number for this subscription.

        A single-document `$inc` is atomic in MongoDB, so concurrent callers
        cannot receive the same number. The unique index on
        (subscription_id, seq) is the backstop if this ever regresses.
        """
        doc = await self.col.find_one_and_update(
            {"subscription_id": subscription_id},
            {"$inc": {"audit_seq": 1}},
            projection={"audit_seq": 1},
            return_document=ReturnDocument.AFTER,
        )
        if doc is None:
            raise KeyError(f"unknown subscription {subscription_id}")
        return int(doc["audit_seq"])
