"""Post-halt backlog reconstruction.

Pure: no I/O, no clock, no policy, no collectibility. Given a halt episode
and the invoices we already have, it answers one question — how much unpaid
historical invoice value belongs to this episode.

That amount is HISTORICAL UNPAID BACKLOG. It is not recoverable revenue.
Collectibility evaluation lives in `app.domain.collectibility` and runs after
this reconstruction.

Lineage is authoritative. An invoice is in the unpaid set only when
`halt_episode_id` matches. We do not infer membership from date windows.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime

from app.domain.enums import InvoiceStatus
from app.models.documents import HaltEpisode, Invoice


@dataclass(frozen=True)
class BacklogResult:
    halt_episode_id: str
    invoice_ids: list[str]
    invoice_count: int
    backlog_amount_paise: int
    oldest_invoice_at: datetime | None
    newest_invoice_at: datetime | None
    halted_at: datetime
    reactivated_at: datetime | None
    halt_duration_days: int

    @property
    def has_outstanding(self) -> bool:
        return self.backlog_amount_paise > 0


def halt_duration_days(halted_at: datetime, reactivated_at: datetime | None) -> int:
    if reactivated_at is None:
        return 0
    return max(0, (reactivated_at - halted_at).days)


def reconstruct_backlog(
    *,
    subscription_id: str,
    episode: HaltEpisode,
    invoices: Sequence[Invoice],
) -> BacklogResult:
    """Filter invoices onto one halt episode. Money stays integer paise."""
    by_id: dict[str, Invoice] = {}
    for invoice in invoices:
        if invoice.subscription_id != subscription_id:
            continue
        if invoice.halt_episode_id != episode.episode_id:
            continue
        if invoice.status is not InvoiceStatus.ISSUED_UNPAID:
            continue
        by_id[invoice.invoice_id] = invoice

    # Billing-period chronology, not ingest time. A late-delivered invoice
    # for February is older debt than a March invoice even if it arrived
    # afterwards (INC-007 taught us those clocks diverge).
    chosen = sorted(by_id.values(), key=lambda i: (i.period_start, i.invoice_id))
    amount = sum(i.amount_paise for i in chosen)
    # sum() of an empty sequence is the int 0, not a float.
    assert isinstance(amount, int)

    return BacklogResult(
        halt_episode_id=episode.episode_id,
        invoice_ids=[i.invoice_id for i in chosen],
        invoice_count=len(chosen),
        backlog_amount_paise=amount,
        oldest_invoice_at=chosen[0].period_start if chosen else None,
        newest_invoice_at=chosen[-1].period_start if chosen else None,
        halted_at=episode.halted_at,
        reactivated_at=episode.reactivated_at,
        halt_duration_days=halt_duration_days(episode.halted_at, episode.reactivated_at),
    )
