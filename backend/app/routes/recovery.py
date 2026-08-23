from fastapi import APIRouter, HTTPException, Query, status

from app.config import get_settings
from app.domain.enums import RecoveryCaseStatus
from app.domain.policy import PolicyContext
from app.domain.time import utcnow
from app.policy import evaluate_v1
from app.routes.deps import (
    Audit,
    Cases,
    Customers,
    Invoices,
    Reconcile,
    Subscriptions,
)
from app.schemas.recovery import (
    ReconcileReportOut,
    RecoveryCaseDetail,
    RecoveryCaseOut,
)
from app.schemas.subscriptions import AuditLogOut, InvoiceOut

router = APIRouter(prefix="/api", tags=["recovery"])


def _relevant_audit(entries, case) -> list:
    wanted = []
    for entry in entries:
        details = entry.details
        if details.get("case_id") == case.case_id:
            wanted.append(entry)
            continue
        episode = details.get("halt_episode_id") or details.get("episode_id")
        if episode == case.halt_episode_id:
            wanted.append(entry)
    return wanted


@router.get("/recovery-cases", response_model=list[RecoveryCaseOut])
async def list_recovery_cases(
    cases: Cases,
    run_id: str = Query(description="Required. Cases are isolated per run."),
    status: RecoveryCaseStatus | None = None,
):
    return [
        RecoveryCaseOut(**c.model_dump())
        for c in await cases.list_by_run(run_id, status)
    ]


@router.post("/recovery-cases/reconcile", response_model=ReconcileReportOut)
async def reconcile_recovery_cases(
    reconcile: Reconcile,
    run_id: str | None = Query(default=None, description="Scope to one run."),
):
    """Find closed halt episodes with unpaid backlog and no case, and create
    the missing cases. Safe to call repeatedly. Pass run_id so a simulation
    repair cannot touch another run."""
    report = await reconcile.reconcile(run_id=run_id)
    return ReconcileReportOut(
        examined_episodes=report.examined_episodes,
        created_case_ids=report.created_case_ids,
        already_present=report.already_present,
        skipped_no_backlog=report.skipped_no_backlog,
    )


@router.get("/recovery-cases/{case_id}", response_model=RecoveryCaseDetail)
async def get_recovery_case(
    case_id: str,
    cases: Cases,
    invoices: Invoices,
    subscriptions: Subscriptions,
    customers: Customers,
):
    case = await cases.get(case_id)
    if case is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "unknown recovery case")

    invoice_docs = await invoices.list_for_ids(case.invoice_ids)
    subscription = await subscriptions.get(case.subscription_id)
    customer = await customers.get(case.customer_id)
    settings = get_settings()

    if subscription is None:
        raise HTTPException(status.HTTP_409_CONFLICT, "case subscription is missing")

    decision = evaluate_v1(
        PolicyContext(
            case_id=case.case_id,
            card_type=subscription.card_type,
            backlog_amount_paise=case.backlog_amount_paise,
            mandate_max_amount_paise=subscription.mandate_max_amount_paise,
            risk_flags=customer.risk_flags if customer else case.risk_flags,
            has_dispute=customer.has_active_dispute if customer else False,
            customer_opted_out=customer.customer_opted_out if customer else False,
            attempt_count=case.attempt_count,
            last_contact_at=case.last_contact_at,
            now=utcnow(),
            max_attempts=settings.policy_max_attempts,
            contact_cooldown_hours=settings.policy_contact_cooldown_hours,
        )
    )
    return RecoveryCaseDetail(
        case=RecoveryCaseOut(**case.model_dump()),
        invoices=[InvoiceOut(**i.model_dump()) for i in invoice_docs],
        policy=decision,
    )


@router.get("/recovery-cases/{case_id}/audit", response_model=list[AuditLogOut])
async def get_recovery_case_audit(case_id: str, cases: Cases, audit: Audit):
    case = await cases.get(case_id)
    if case is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "unknown recovery case")
    entries = await audit.list_for_subscription(case.subscription_id)
    return [AuditLogOut(**e.model_dump()) for e in _relevant_audit(entries, case)]
