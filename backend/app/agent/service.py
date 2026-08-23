"""Deterministic agent orchestration. LLM is never consulted for the action."""

from __future__ import annotations

from uuid import uuid4

from app.agent.executor import SimulatedExecutor
from app.agent.stop import stop_before_action
from app.agent.validator import ActionValidator
from app.config import get_settings
from app.domain.enums import (
    ActionType,
    Actor,
    AgentRunStatus,
    AuditEventType,
    RecoveryActionStatus,
    RecoveryCaseStatus,
    StopReason,
)
from app.domain.policy import PolicyContext, PolicyDecision
from app.domain.time import utcnow
from app.llm.explanation import CaseExplanationService
from app.llm.facts import explanation_facts
from app.llm.provider import get_language_provider
from app.ml.case_view import build_case_view
from app.ml.predict import try_analyze_view
from app.models.agent import AgentRun, RecoveryAction
from app.models.documents import Customer, RecoveryCase, Subscription
from app.policy import evaluate_v1
from app.repositories.agent_runs import AgentRunRepository
from app.repositories.budgets import BudgetRepository
from app.repositories.customers import CustomerRepository
from app.repositories.recovery_actions import RecoveryActionRepository
from app.repositories.recovery_cases import RecoveryCaseRepository
from app.repositories.simulation_runs import SimulationRunRepository
from app.repositories.subscriptions import SubscriptionRepository
from app.services.audit import AuditTrail
from app.simulator.costs import consumes_budget
from app.simulator.oracle import OracleCase
from app.simulator.world import DECISION_NOW


def recommend_action(policy: PolicyDecision, analysis: dict | None) -> ActionType:
    if analysis and analysis.get("selected_action"):
        chosen = ActionType(analysis["selected_action"])
        if chosen in policy.allowed_actions:
            return chosen
    if policy.requires_escalation and ActionType.ESCALATE_TO_MERCHANT in policy.allowed_actions:
        return ActionType.ESCALATE_TO_MERCHANT
    if ActionType.SEND_PAYMENT_LINK in policy.allowed_actions:
        return ActionType.SEND_PAYMENT_LINK
    return ActionType.NO_ACTION


def _policy(
    case: RecoveryCase,
    customer: Customer,
    subscription: Subscription,
    *,
    ignore_contact_flags: bool = False,
) -> PolicyDecision:
    settings = get_settings()
    return evaluate_v1(
        PolicyContext(
            case_id=case.case_id,
            card_type=subscription.card_type,
            backlog_amount_paise=case.backlog_amount_paise,
            mandate_max_amount_paise=subscription.mandate_max_amount_paise,
            risk_flags=customer.risk_flags,
            has_dispute=False if ignore_contact_flags else customer.has_active_dispute,
            customer_opted_out=(
                False if ignore_contact_flags else customer.customer_opted_out
            ),
            attempt_count=case.attempt_count,
            last_contact_at=case.last_contact_at,
            now=DECISION_NOW,
            max_attempts=settings.max_recovery_attempts,
            contact_cooldown_hours=settings.policy_contact_cooldown_hours,
        )
    )


def evaluate_case_policy(
    case: RecoveryCase, customer: Customer, subscription: Subscription
) -> PolicyDecision:
    return _policy(case, customer, subscription)


class RecoveryAgent:
    def __init__(
        self,
        cases: RecoveryCaseRepository,
        customers: CustomerRepository,
        subscriptions: SubscriptionRepository,
        runs: SimulationRunRepository,
        agent_runs: AgentRunRepository,
        actions: RecoveryActionRepository,
        budgets: BudgetRepository,
        trail: AuditTrail,
        validator: ActionValidator | None = None,
        executor: SimulatedExecutor | None = None,
        explanations: CaseExplanationService | None = None,
    ) -> None:
        self.cases = cases
        self.customers = customers
        self.subscriptions = subscriptions
        self.runs = runs
        self.agent_runs = agent_runs
        self.actions = actions
        self.budgets = budgets
        self.trail = trail
        self.validator = validator or ActionValidator()
        self.executor = executor or SimulatedExecutor()
        self.explanations = explanations or CaseExplanationService(get_language_provider())

    async def _bundle(self, case_id: str):
        case = await self.cases.get(case_id)
        if case is None:
            raise KeyError(case_id)
        customer = await self.customers.get(case.customer_id)
        subscription = await self.subscriptions.get(case.subscription_id)
        if customer is None or subscription is None:
            raise RuntimeError("case entities are missing")
        return case, customer, subscription

    async def _limit(self, run_id: str) -> int:
        record = await self.runs.get(run_id)
        if record is not None:
            return record.config.intervention_budget
        return get_settings().intervention_budget_default

    async def plan(self, case_id: str, *, prefer_llm: bool = False) -> dict:
        case, customer, subscription = await self._bundle(case_id)
        policy = evaluate_case_policy(case, customer, subscription)
        view = build_case_view(case, customer, subscription)
        analysis = try_analyze_view(view)
        recommended = recommend_action(policy, analysis)
        facts = explanation_facts(case, policy, analysis)
        facts["recommended_action"] = recommended.value
        explanation, source = self.explanations.explain(facts, prefer_llm=prefer_llm)
        await self.trail.record(
            run_id=case.run_id,
            subscription_id=case.subscription_id,
            event_type=AuditEventType.POLICY_EVALUATED,
            details={"case_id": case.case_id, "phase": "plan"},
            actor=Actor.AGENT,
        )
        if analysis:
            await self.trail.record(
                run_id=case.run_id,
                subscription_id=case.subscription_id,
                event_type=AuditEventType.MODEL_ANALYZED,
                details={
                    "case_id": case.case_id,
                    "selected_action": analysis.get("selected_action"),
                    "model_version": analysis.get("model_version"),
                },
                actor=Actor.AGENT,
            )
        await self.trail.record(
            run_id=case.run_id,
            subscription_id=case.subscription_id,
            event_type=AuditEventType.ACTION_PROPOSED,
            details={"case_id": case.case_id, "action": recommended.value},
            actor=Actor.AGENT,
        )
        return {
            "case_id": case.case_id,
            "run_id": case.run_id,
            "policy": policy.model_dump(),
            "model_analysis": analysis,
            "recommended_action": recommended.value,
            "expected_incremental_recovery_paise": (
                analysis.get("expected_incremental_recovery_paise") if analysis else 0
            ),
            "estimated_uplift": analysis.get("estimated_uplift") if analysis else 0.0,
            "deterministic_explanation": explanation.model_dump()
            if source == "deterministic"
            else CaseExplanationService(None).explain(facts)[0].model_dump(),
            "llm_explanation": explanation.model_dump() if source == "llm" else None,
            "explanation_source": source,
            "synthetic": True,
        }

    async def execute(
        self,
        case_id: str,
        *,
        prefer_llm: bool = False,
        idempotency_key: str | None = None,
    ) -> dict:
        settings = get_settings()
        case, customer, subscription = await self._bundle(case_id)
        # Latest policy is what the validator applies. The candidate action is
        # scored without dispute/opt-out so a mid-flight flag change is a
        # blocked execution, not a silent model replan.
        policy = evaluate_case_policy(case, customer, subscription)
        proposal_customer = customer.model_copy(
            update={
                "customer_opted_out": False,
                "has_active_dispute": False,
                "risk_flags": [],
            }
        )
        proposal_policy = _policy(
            case, proposal_customer, subscription, ignore_contact_flags=True
        )
        view = build_case_view(case, proposal_customer, subscription)
        analysis = try_analyze_view(view)
        recommended = recommend_action(proposal_policy, analysis)
        ev = (
            int(analysis.get("expected_incremental_recovery_paise") or 0)
            if analysis and case.synthetic_case_key
            else None
        )
        limit = await self._limit(case.run_id)
        remaining = await self.budgets.remaining(case.run_id, limit)
        attempt = case.attempt_count + 1
        now = utcnow()
        agent = AgentRun(
            agent_run_id=f"ar_{uuid4().hex[:12]}",
            run_id=case.run_id,
            case_id=case.case_id,
            model_version=(analysis or {}).get("model_version") or "",
            policy_version=policy.policy_version,
            recommended_action=recommended,
            attempt_number=attempt,
            status=AgentRunStatus.PLANNED,
            started_at=now,
        )
        await self.agent_runs.insert(agent)
        facts = explanation_facts(case, policy, analysis)
        facts["recommended_action"] = recommended.value
        explanation, source = self.explanations.explain(facts, prefer_llm=prefer_llm)
        agent.explanation_source = source

        async def audit(event: AuditEventType, details: dict, actor: Actor = Actor.AGENT):
            entry = await self.trail.record(
                run_id=case.run_id,
                subscription_id=case.subscription_id,
                event_type=event,
                details={"case_id": case.case_id, "agent_run_id": agent.agent_run_id, **details},
                actor=actor,
            )
            agent.trace.append(
                {
                    "event_type": event.value,
                    "audit_id": entry.audit_id,
                    "details": details,
                }
            )

        await audit(AuditEventType.POLICY_EVALUATED, {"phase": "observe"})
        if analysis:
            await audit(
                AuditEventType.MODEL_ANALYZED,
                {"selected_action": analysis.get("selected_action")},
            )
        await audit(AuditEventType.ACTION_PROPOSED, {"action": recommended.value})

        early = stop_before_action(
            case=case,
            customer=customer,
            decision=policy,
            recommended=recommended,
            incremental_ev_paise=ev,
            max_attempts=settings.max_recovery_attempts,
            hard_cap=settings.agent_hard_iteration_cap,
            budget_remaining=remaining,
        )
        # Dispute / opt-out / policy blocks go through the validator so the
        # revalidation audit is visible. Hard stops do not need a candidate action.
        if early in {
            StopReason.CASE_CLOSED,
            StopReason.MAX_ATTEMPTS_REACHED,
            StopReason.HARD_ITERATION_CAP,
            StopReason.NEGATIVE_OR_ZERO_EV,
        }:
            return await self._halt(agent, case, early, policy, None)

        await audit(AuditEventType.ACTION_VALIDATION_STARTED, {"action": recommended.value})
        key = idempotency_key or f"{case.run_id}:{case.case_id}:{recommended.value}:{attempt}"
        existing = await self.actions.get_by_key(key)
        if existing and existing.status is RecoveryActionStatus.EXECUTED:
            agent.status = AgentRunStatus.EXECUTED
            agent.validated_action = existing.action
            agent.completed_at = existing.executed_at or utcnow()
            agent.stop_reason = StopReason.ALREADY_EXECUTED
            await self.agent_runs.save(agent)
            return self._payload(agent, existing, None, explanation, source)
        validation = self.validator.validate(
            case=case,
            customer=customer,
            subscription=subscription,
            action=recommended,
            planning_decision=policy,
            budget_remaining=remaining,
            now=DECISION_NOW,
            existing_action=bool(existing and existing.status is RecoveryActionStatus.EXECUTED),
        )
        await audit(
            AuditEventType.POLICY_REVALIDATED,
            {
                "allowed": [a.value for a in validation.execution_decision.allowed_actions],
                "blocked": [a.value for a in validation.execution_decision.blocked_actions],
            },
            actor=Actor.VALIDATOR,
        )
        if not validation.ok:
            await audit(
                AuditEventType.ACTION_BLOCKED,
                {"stop_reason": validation.stop_reason.value if validation.stop_reason else ""},
                actor=Actor.VALIDATOR,
            )
            reason = validation.stop_reason or StopReason.VALIDATION_FAILED
            if validation.escalate or recommended is ActionType.ESCALATE_TO_MERCHANT:
                return await self._escalate(agent, case, reason, validation.execution_decision)
            return await self._halt(agent, case, reason, validation.execution_decision, validation)

        record = RecoveryAction(
            action_id=f"ra_{uuid4().hex[:12]}",
            agent_run_id=agent.agent_run_id,
            run_id=case.run_id,
            case_id=case.case_id,
            action=recommended,
            attempt_number=attempt,
            idempotency_key=key,
            policy_version=policy.policy_version,
            model_version=agent.model_version,
            status=RecoveryActionStatus.VALIDATED,
            created_at=now,
        )
        record, created = await self.actions.create_if_absent(record)
        if not created:
            agent.status = (
                AgentRunStatus.EXECUTED
                if record.status is RecoveryActionStatus.EXECUTED
                else AgentRunStatus.STOPPED
            )
            agent.validated_action = record.action
            agent.completed_at = record.executed_at or utcnow()
            agent.stop_reason = StopReason.ALREADY_EXECUTED
            await self.agent_runs.save(agent)
            return self._payload(agent, record, validation, explanation, source)

        claimed = False
        if consumes_budget(recommended) and not record.budget_claimed:
            claimed = await self.budgets.claim(case.run_id, limit)
            if not claimed:
                record.status = RecoveryActionStatus.BLOCKED
                record.stop_reason = StopReason.BUDGET_EXHAUSTED
                await self.actions.save(record)
                await audit(AuditEventType.ACTION_BLOCKED, {"stop_reason": "BUDGET_EXHAUSTED"})
                return await self._halt(
                    agent,
                    case,
                    StopReason.BUDGET_EXHAUSTED,
                    validation.execution_decision,
                    validation,
                )
            record.budget_claimed = True
            await self.actions.save(record)

        await audit(AuditEventType.ACTION_VALIDATED, {"action": recommended.value})
        agent.status = AgentRunStatus.VALIDATED
        agent.validated_action = recommended

        sim = await self.runs.get(case.run_id)
        seed = sim.seed if sim is not None else get_settings().sim_default_seed
        try:
            outcome = self.executor.execute(
                OracleCase(
                    case_id=case.case_id,
                    synthetic_case_key=case.synthetic_case_key or case.case_id,
                    synthetic_customer_key=case.synthetic_customer_key or case.customer_id,
                    backlog_amount_paise=case.backlog_amount_paise,
                    historical_payment_success_rate=customer.historical_payment_success_rate,
                    has_dispute=customer.has_active_dispute,
                    customer_opted_out=customer.customer_opted_out,
                ),
                recommended,
                seed,
            )
        except Exception:
            record.status = RecoveryActionStatus.FAILED
            record.stop_reason = StopReason.SYSTEM_FAILURE
            await self.actions.save(record)
            await audit(
                AuditEventType.ACTION_BLOCKED,
                {"stop_reason": StopReason.SYSTEM_FAILURE.value},
            )
            return await self._halt(
                agent,
                case,
                StopReason.SYSTEM_FAILURE,
                validation.execution_decision,
                validation,
                record,
            )
        record.status = RecoveryActionStatus.EXECUTED
        record.outcome = outcome.outcome
        record.amount_recovered_paise = outcome.amount_recovered_paise
        record.executed_at = utcnow()
        await self.actions.save(record)
        contacted = recommended is ActionType.SEND_PAYMENT_LINK
        await self.cases.record_attempt(case.case_id, now=record.executed_at, contacted=contacted)
        await audit(
            AuditEventType.ACTION_EXECUTED,
            {"action": recommended.value, "synthetic": True},
        )
        await audit(
            AuditEventType.OUTCOME_OBSERVED,
            {
                "outcome": outcome.outcome,
                "amount_recovered_paise": outcome.amount_recovered_paise,
            },
        )

        if outcome.outcome == "paid":
            await self.cases.close_recovered(
                case.case_id,
                amount_recovered_paise=outcome.amount_recovered_paise,
                now=record.executed_at,
            )
            await audit(
                AuditEventType.CASE_CLOSED,
                {"amount_recovered_paise": outcome.amount_recovered_paise},
            )
            return await self._halt(
                agent,
                case,
                StopReason.RECOVERY_SUCCEEDED,
                validation.execution_decision,
                validation,
                record,
            )
        if recommended is ActionType.ESCALATE_TO_MERCHANT:
            return await self._escalate(
                agent, case, StopReason.POLICY_BLOCKED, validation.execution_decision, record
            )
        if attempt >= settings.max_recovery_attempts:
            return await self._halt(
                agent,
                case,
                StopReason.MAX_ATTEMPTS_REACHED,
                validation.execution_decision,
                validation,
                record,
            )
        agent.status = AgentRunStatus.EXECUTED
        agent.completed_at = record.executed_at
        await self.agent_runs.save(agent)
        return self._payload(agent, record, validation, explanation, source)

    async def _halt(
        self,
        agent: AgentRun,
        case: RecoveryCase,
        reason: StopReason,
        policy: PolicyDecision,
        validation,
        record: RecoveryAction | None = None,
    ) -> dict:
        if reason is StopReason.ACTIVE_DISPUTE:
            agent.status = AgentRunStatus.ESCALATED
        elif reason is StopReason.SYSTEM_FAILURE:
            agent.status = AgentRunStatus.FAILED
        else:
            agent.status = AgentRunStatus.STOPPED
        if reason is StopReason.RECOVERY_SUCCEEDED:
            agent.status = AgentRunStatus.EXECUTED
        agent.stop_reason = reason
        agent.completed_at = utcnow()
        if validation is not None:
            agent.next_eligible_at = validation.next_eligible_at
        await self.trail.record(
            run_id=case.run_id,
            subscription_id=case.subscription_id,
            event_type=AuditEventType.AGENT_STOPPED,
            details={"case_id": case.case_id, "stop_reason": reason.value},
            actor=Actor.AGENT,
        )
        agent.trace.append({"event_type": "AGENT_STOPPED", "stop_reason": reason.value})
        await self.agent_runs.save(agent)
        return self._payload(agent, record, validation, None, "deterministic")

    async def _escalate(
        self,
        agent: AgentRun,
        case: RecoveryCase,
        reason: StopReason,
        policy: PolicyDecision,
        record: RecoveryAction | None = None,
    ) -> dict:
        await self.cases.update_status(case.case_id, RecoveryCaseStatus.ESCALATED, utcnow())
        agent.status = AgentRunStatus.ESCALATED
        agent.stop_reason = reason
        agent.completed_at = utcnow()
        await self.trail.record(
            run_id=case.run_id,
            subscription_id=case.subscription_id,
            event_type=AuditEventType.AGENT_ESCALATED,
            details={"case_id": case.case_id, "stop_reason": reason.value},
            actor=Actor.AGENT,
        )
        agent.trace.append({"event_type": "AGENT_ESCALATED", "stop_reason": reason.value})
        await self.agent_runs.save(agent)
        payload = self._payload(agent, record, None, None, "deterministic")
        payload["escalation"] = {
            "reason_codes": [c.value for c in policy.reason_codes],
            "case_id": case.case_id,
            "backlog_amount_paise": case.backlog_amount_paise,
            "policy_constraints": [c.value for c in policy.reason_codes],
            "last_attempt": agent.attempt_number,
            "recommended_human_next_step": (
                "Review the dispute or opt-out with the merchant. "
                "Do not attempt automated collection."
            ),
            "synthetic": True,
        }
        return payload

    def _payload(self, agent, record, validation, explanation, source) -> dict:
        return {
            "agent_run_id": agent.agent_run_id,
            "run_id": agent.run_id,
            "case_id": agent.case_id,
            "status": agent.status.value,
            "stop_reason": agent.stop_reason.value if agent.stop_reason else None,
            "recommended_action": agent.recommended_action.value,
            "validated_action": agent.validated_action.value if agent.validated_action else None,
            "attempt_number": agent.attempt_number,
            "trace": agent.trace,
            "action": record.model_dump() if record else None,
            "planning_policy": validation.planning_decision.model_dump() if validation else None,
            "execution_policy": validation.execution_decision.model_dump() if validation else None,
            "explanation": explanation.model_dump() if explanation else None,
            "explanation_source": source,
            "next_eligible_at": (
                validation.next_eligible_at.isoformat()
                if validation and validation.next_eligible_at
                else None
            ),
            "synthetic": True,
            "simulated": True,
        }
