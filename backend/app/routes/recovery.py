from fastapi import APIRouter, HTTPException, Query, status

from app.agent.service import evaluate_case_policy
from app.config import get_settings
from app.domain.enums import Actor, AuditEventType, RecoveryCaseStatus
from app.domain.policy import PolicyContext, PolicyDecision
from app.domain.time import utcnow
from app.llm.explanation import CaseExplanationService
from app.llm.facts import explanation_facts, qa_facts
from app.llm.grounding import extraction_is_supported
from app.llm.provider import get_language_provider
from app.ml.case_view import build_case_view
from app.ml.predict import try_analyze_view
from app.models.documents import Customer, RecoveryCase, Subscription
from app.policy import evaluate_v1
from app.routes.deps import (
    Audit,
    Cases,
    Customers,
    Invoices,
    Reconcile,
    Subscriptions,
)
from app.schemas.agent import AskRequest, ExtractRequest
from app.schemas.recovery import (
    ReconcileReportOut,
    RecoveryCaseDetail,
    RecoveryCaseOut,
)
from app.schemas.subscriptions import AuditLogOut, HaltEpisodeOut, InvoiceOut
from app.services.audit import AuditTrail


def _policy_status(decision: PolicyDecision) -> str:
    if decision.stop:
        return "stopped"
    if decision.requires_escalation:
        return "escalation_required"
    if decision.blocked_actions:
        return "restricted"
    return "eligible"


def _decision(
    case: RecoveryCase, customer: Customer | None, subscription: Subscription
) -> PolicyDecision:
    settings = get_settings()
    return evaluate_v1(
        PolicyContext(
            case_id=case.case_id,
            card_type=subscription.card_type,
            backlog_amount_paise=case.backlog_amount_paise,
            mandate_max_amount_paise=subscription.mandate_max_amount_paise,
            risk_flags=customer.risk_flags if customer else case.risk_flags,
            has_dispute=(
                customer.has_active_dispute if customer else case.has_active_dispute
            ),
            customer_opted_out=(
                customer.customer_opted_out if customer else case.customer_opted_out
            ),
            attempt_count=case.attempt_count,
            last_contact_at=case.last_contact_at,
            now=utcnow(),
            max_attempts=settings.policy_max_attempts,
            contact_cooldown_hours=settings.policy_contact_cooldown_hours,
        )
    )


def _case_out(
    case: RecoveryCase,
    customer: Customer | None,
    subscription: Subscription | None,
) -> RecoveryCaseOut:
    decision = (
        _decision(case, customer, subscription) if subscription is not None else None
    )
    analysis = None
    if customer is not None and subscription is not None:
        analysis = try_analyze_view(build_case_view(case, customer, subscription))
    return RecoveryCaseOut(
        **case.model_dump(),
        customer_name=customer.name if customer else case.customer_id,
        policy_status=_policy_status(decision) if decision else "eligible",
        allowed_actions=[a.value for a in decision.allowed_actions] if decision else [],
        blocked_actions=[a.value for a in decision.blocked_actions] if decision else [],
        requires_escalation=decision.requires_escalation if decision else False,
        stop=decision.stop if decision else False,
        model_analysis=analysis,
    )

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
    customers: Customers,
    subscriptions: Subscriptions,
    run_id: str = Query(description="Required. Cases are isolated per run."),
    status: RecoveryCaseStatus | None = None,
):
    rows = await cases.list_by_run(run_id, status)
    customers_by_id = await customers.get_many([c.customer_id for c in rows])
    subs_by_id = await subscriptions.get_many([c.subscription_id for c in rows])
    return [
        _case_out(
            case,
            customers_by_id.get(case.customer_id),
            subs_by_id.get(case.subscription_id),
        )
        for case in rows
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

    if subscription is None:
        raise HTTPException(status.HTTP_409_CONFLICT, "case subscription is missing")

    decision = _decision(case, customer, subscription)
    case_out = _case_out(case, customer, subscription)
    return RecoveryCaseDetail(
        case=case_out,
        invoices=[InvoiceOut(**i.model_dump()) for i in invoice_docs],
        policy=decision,
        customer_name=customer.name if customer else case.customer_id,
        subscription_status=subscription.status.value,
        subscription_created_at=subscription.created_at,
        halt_episodes=[
            HaltEpisodeOut(**episode.model_dump())
            for episode in subscription.halt_episodes
        ],
        model_analysis=case_out.model_analysis,
    )


@router.get("/recovery-cases/{case_id}/analysis")
async def get_recovery_case_analysis(
    case_id: str,
    cases: Cases,
    subscriptions: Subscriptions,
    customers: Customers,
):
    case = await cases.get(case_id)
    if case is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "unknown recovery case")
    subscription = await subscriptions.get(case.subscription_id)
    customer = await customers.get(case.customer_id)
    if subscription is None or customer is None:
        raise HTTPException(status.HTTP_409_CONFLICT, "case entities are missing")
    analysis = try_analyze_view(build_case_view(case, customer, subscription))
    if analysis is None:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "No valid active recovery model exists. Train one with POST /api/model/train.",
        )
    return analysis


@router.get("/recovery-cases/{case_id}/explanation")
async def get_recovery_case_explanation(
    case_id: str,
    cases: Cases,
    subscriptions: Subscriptions,
    customers: Customers,
    mode: str = Query(default="deterministic"),
):
    case = await cases.get(case_id)
    if case is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "unknown recovery case")
    subscription = await subscriptions.get(case.subscription_id)
    customer = await customers.get(case.customer_id)
    if subscription is None or customer is None:
        raise HTTPException(status.HTTP_409_CONFLICT, "case entities are missing")
    policy = evaluate_case_policy(case, customer, subscription)
    analysis = try_analyze_view(build_case_view(case, customer, subscription))
    facts = explanation_facts(case, policy, analysis)
    prefer = mode == "llm"
    explanation, source = CaseExplanationService(get_language_provider()).explain(
        facts, prefer_llm=prefer
    )
    return {
        "explanation": explanation.model_dump(),
        "source": source,
        "requested_mode": mode,
        "synthetic": True,
    }


@router.post("/recovery-cases/{case_id}/ask")
async def ask_recovery_case(
    case_id: str,
    body: AskRequest,
    cases: Cases,
    subscriptions: Subscriptions,
    customers: Customers,
    audit: Audit,
):
    case = await cases.get(case_id)
    if case is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "unknown recovery case")
    subscription = await subscriptions.get(case.subscription_id)
    customer = await customers.get(case.customer_id)
    if subscription is None or customer is None:
        raise HTTPException(status.HTTP_409_CONFLICT, "case entities are missing")
    policy = evaluate_case_policy(case, customer, subscription)
    analysis = try_analyze_view(build_case_view(case, customer, subscription))
    entries = _relevant_audit(await audit.list_for_subscription(case.subscription_id), case)
    facts = qa_facts(case, policy, analysis, entries)
    answer, source = CaseExplanationService(get_language_provider()).ask(
        body.question, facts, prefer_llm=body.prefer_llm
    )
    return {
        "answer": answer.answer,
        "source": source,
        "grounding": answer.grounding,
        "insufficient_information": answer.insufficient_information,
        "synthetic": True,
    }


@router.post("/recovery-cases/{case_id}/extract")
async def extract_recovery_context(
    case_id: str,
    body: ExtractRequest,
    cases: Cases,
    customers: Customers,
    subscriptions: Subscriptions,
    audit: Audit,
):
    case = await cases.get(case_id)
    if case is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "unknown recovery case")
    proposal, source = CaseExplanationService(get_language_provider()).extract(
        body.source_text, prefer_llm=body.prefer_llm
    )
    supported = extraction_is_supported(proposal, body.source_text)
    trail = AuditTrail(subscriptions, audit)
    await trail.record(
        run_id=case.run_id,
        subscription_id=case.subscription_id,
        event_type=AuditEventType.CONTEXT_EXTRACTION_PROPOSED,
        details={"case_id": case.case_id, "source": source, "apply": body.apply},
        actor=Actor.LANGUAGE_LAYER,
    )
    applied = False
    has_facts = (
        proposal.has_dispute is True
        or proposal.customer_opted_out is True
        or bool(proposal.risk_signals)
    )
    if body.apply and supported and has_facts:
        await customers.set_flags(
            case.customer_id,
            has_active_dispute=proposal.has_dispute,
            customer_opted_out=proposal.customer_opted_out,
            risk_flags=proposal.risk_signals or None,
        )
        await trail.record(
            run_id=case.run_id,
            subscription_id=case.subscription_id,
            event_type=AuditEventType.CONTEXT_UPDATE_ACCEPTED,
            details={"case_id": case.case_id, "proposal": proposal.model_dump()},
            actor=Actor.SYSTEM,
        )
        applied = True
    elif body.apply and not supported:
        await trail.record(
            run_id=case.run_id,
            subscription_id=case.subscription_id,
            event_type=AuditEventType.CONTEXT_UPDATE_REJECTED,
            details={"case_id": case.case_id, "reason": "unsupported_extraction"},
            actor=Actor.SYSTEM,
        )
    return {
        "proposal": proposal.model_dump(),
        "source": source,
        "supported": supported,
        "applied": applied,
        "synthetic": True,
    }


@router.get("/recovery-cases/{case_id}/audit", response_model=list[AuditLogOut])
async def get_recovery_case_audit(case_id: str, cases: Cases, audit: Audit):
    case = await cases.get(case_id)
    if case is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "unknown recovery case")
    entries = await audit.list_for_subscription(case.subscription_id)
    return [AuditLogOut(**e.model_dump()) for e in _relevant_audit(entries, case)]
