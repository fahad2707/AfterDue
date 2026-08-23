from datetime import UTC, datetime, timedelta

from app.domain.backlog import reconstruct_backlog
from app.domain.enums import InvoiceStatus
from app.models.documents import HaltEpisode, Invoice

T0 = datetime(2026, 2, 1, 10, 0, tzinfo=UTC)


def episode(
    episode_id: str = "he_1",
    *,
    halted_at: datetime = T0,
    days_open: int = 90,
    invoice_ids: list[str] | None = None,
) -> HaltEpisode:
    return HaltEpisode(
        episode_id=episode_id,
        halted_at=halted_at,
        reactivated_at=halted_at + timedelta(days=days_open),
        invoice_ids=invoice_ids or [],
    )


def invoice(
    invoice_id: str,
    *,
    halt_episode_id: str | None,
    status: InvoiceStatus = InvoiceStatus.ISSUED_UNPAID,
    amount: int = 499900,
    created_at: datetime = T0,
    period_start: datetime | None = None,
    subscription_id: str = "sub_priya",
    cycle: str = "2026-02",
) -> Invoice:
    start = period_start if period_start is not None else created_at
    return Invoice(
        invoice_id=invoice_id,
        run_id="run_test",
        subscription_id=subscription_id,
        billing_cycle=cycle,
        period_start=start,
        period_end=start + timedelta(days=30),
        amount_paise=amount,
        status=status,
        halt_episode_id=halt_episode_id,
        generated_during_halt=halt_episode_id is not None,
        created_at=created_at,
    )


def test_unpaid_historical_invoices_included():
    ep = episode(invoice_ids=["inv_1", "inv_2"])
    result = reconstruct_backlog(
        subscription_id="sub_priya",
        episode=ep,
        invoices=[
            invoice("inv_1", halt_episode_id="he_1", created_at=T0 + timedelta(days=10)),
            invoice("inv_2", halt_episode_id="he_1", created_at=T0 + timedelta(days=40)),
        ],
    )
    assert result.invoice_ids == ["inv_1", "inv_2"]
    assert result.invoice_count == 2


def test_paid_historical_invoices_excluded():
    ep = episode(invoice_ids=["inv_paid", "inv_open"])
    result = reconstruct_backlog(
        subscription_id="sub_priya",
        episode=ep,
        invoices=[
            invoice("inv_paid", halt_episode_id="he_1", status=InvoiceStatus.PAID),
            invoice("inv_open", halt_episode_id="he_1"),
        ],
    )
    assert result.invoice_ids == ["inv_open"]
    assert result.backlog_amount_paise == 499900


def test_active_period_invoices_excluded():
    ep = episode()
    result = reconstruct_backlog(
        subscription_id="sub_priya",
        episode=ep,
        invoices=[invoice("inv_active", halt_episode_id=None)],
    )
    assert result.invoice_ids == []
    assert result.backlog_amount_paise == 0


def test_invoices_from_another_halt_episode_excluded():
    ep = episode("he_1")
    result = reconstruct_backlog(
        subscription_id="sub_priya",
        episode=ep,
        invoices=[
            invoice("inv_other", halt_episode_id="he_2"),
            invoice("inv_ours", halt_episode_id="he_1"),
        ],
    )
    assert result.invoice_ids == ["inv_ours"]


def test_zero_backlog_is_zero_integer_paise():
    result = reconstruct_backlog(
        subscription_id="sub_priya", episode=episode(), invoices=[]
    )
    assert result.backlog_amount_paise == 0
    assert isinstance(result.backlog_amount_paise, int)
    assert result.has_outstanding is False


def test_amount_sum_is_integer_paise():
    result = reconstruct_backlog(
        subscription_id="sub_priya",
        episode=episode(),
        invoices=[
            invoice("a", halt_episode_id="he_1", amount=499900),
            invoice("b", halt_episode_id="he_1", amount=499900),
            invoice("c", halt_episode_id="he_1", amount=499900),
        ],
    )
    assert result.backlog_amount_paise == 1499700
    assert isinstance(result.backlog_amount_paise, int)
    assert type(result.backlog_amount_paise) is int


def test_oldest_and_newest_invoice_use_billing_period_not_ingest_time():
    """Debt age is the billing cycle, not when the event arrived.

    A February invoice delivered after a March invoice is still older debt.
    """
    feb = datetime(2026, 2, 1, tzinfo=UTC)
    mar = datetime(2026, 3, 1, tzinfo=UTC)
    result = reconstruct_backlog(
        subscription_id="sub_priya",
        episode=episode(),
        invoices=[
            invoice(
                "late_arrival_feb",
                halt_episode_id="he_1",
                created_at=datetime(2026, 5, 1, tzinfo=UTC),
                period_start=feb,
                cycle="2026-02",
            ),
            invoice(
                "on_time_mar",
                halt_episode_id="he_1",
                created_at=datetime(2026, 3, 10, tzinfo=UTC),
                period_start=mar,
                cycle="2026-03",
            ),
        ],
    )
    assert result.oldest_invoice_at == feb
    assert result.newest_invoice_at == mar
    assert result.invoice_ids == ["late_arrival_feb", "on_time_mar"]


def test_halt_duration_is_calendar_days():
    halted = datetime(2026, 2, 1, 10, 0, tzinfo=UTC)
    ep = episode(halted_at=halted, days_open=90)
    result = reconstruct_backlog(
        subscription_id="sub_priya", episode=ep, invoices=[]
    )
    assert result.halt_duration_days == 90
    assert result.halted_at == halted
    assert result.reactivated_at == halted + timedelta(days=90)


def test_duplicate_invoice_ids_are_not_double_counted():
    inv = invoice("inv_1", halt_episode_id="he_1")
    result = reconstruct_backlog(
        subscription_id="sub_priya",
        episode=episode(),
        invoices=[inv, inv],
    )
    assert result.invoice_count == 1
    assert result.backlog_amount_paise == 499900


def test_wrong_subscription_is_excluded():
    result = reconstruct_backlog(
        subscription_id="sub_priya",
        episode=episode(),
        invoices=[
            invoice("inv_x", halt_episode_id="he_1", subscription_id="sub_other")
        ],
    )
    assert result.invoice_ids == []
