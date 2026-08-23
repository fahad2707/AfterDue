from app.domain.backlog import BacklogResult, reconstruct_backlog
from app.models.documents import Subscription
from app.repositories.invoices import InvoiceRepository


class BacklogBuilder:
    """Thin I/O wrapper around the pure backlog function."""

    def __init__(self, invoices: InvoiceRepository) -> None:
        self.invoices = invoices

    async def for_episode(
        self, subscription: Subscription, halt_episode_id: str
    ) -> BacklogResult:
        episode = next(
            (
                e
                for e in subscription.halt_episodes
                if e.episode_id == halt_episode_id
            ),
            None,
        )
        if episode is None:
            raise KeyError(
                f"halt episode {halt_episode_id} not on {subscription.subscription_id}"
            )
        invoices = await self.invoices.list_for_subscription(
            subscription.subscription_id
        )
        return reconstruct_backlog(
            subscription_id=subscription.subscription_id,
            episode=episode,
            invoices=invoices,
        )
