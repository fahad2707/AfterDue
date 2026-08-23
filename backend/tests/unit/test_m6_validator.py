from app.agent.stop import stop_before_action
from app.agent.validator import ActionValidator
from app.domain.enums import ActionType, CardType, RecoveryCaseStatus, StopReason
from app.domain.policy import PolicyContext
from app.models.documents import Customer, RecoveryCase, Subscription
from app.policy import evaluate_v1
from app.simulator.world import DECISION_NOW


def _case(**kw) -> RecoveryCase:
    defaults = dict(
        case_id="case_1",
        run_id="run_1",
        subscription_id="sub_1",
        customer_id="cust_1",
        halt_episode_id="he_1",
        status=RecoveryCaseStatus.OPEN,
        invoice_ids=["inv_1"],
        invoice_count=1,
        backlog_amount_paise=499900,
        oldest_invoice_at=DECISION_NOW,
        newest_invoice_at=DECISION_NOW,
        halted_at=DECISION_NOW,
        reactivated_at=DECISION_NOW,
        halt_duration_days=30,
        card_type=CardType.INTERNATIONAL,
        policy_version="v1",
        attempt_count=0,
        last_contact_at=None,
        created_at=DECISION_NOW,
        updated_at=DECISION_NOW,
    )
    defaults.update(kw)
    return RecoveryCase(**defaults)


def _customer(**kw) -> Customer:
    defaults = dict(
        customer_id="cust_1",
        run_id="run_1",
        name="Test",
        created_at=DECISION_NOW,
    )
    defaults.update(kw)
    return Customer(**defaults)


def _sub(**kw) -> Subscription:
    defaults = dict(
        subscription_id="sub_1",
        run_id="run_1",
        customer_id="cust_1",
        status="active",
        plan_amount_paise=499900,
        card_type=CardType.INTERNATIONAL,
        mandate_max_amount_paise=499900,
        created_at=DECISION_NOW,
        updated_at=DECISION_NOW,
        last_state_change_at=DECISION_NOW,
        audit_seq=0,
    )
    defaults.update(kw)
    return Subscription(**defaults)


def _plan(case, customer, sub):
    return evaluate_v1(
        PolicyContext(
            case_id=case.case_id,
            card_type=sub.card_type,
            backlog_amount_paise=case.backlog_amount_paise,
            mandate_max_amount_paise=sub.mandate_max_amount_paise,
            risk_flags=customer.risk_flags,
            has_dispute=customer.has_active_dispute,
            customer_opted_out=customer.customer_opted_out,
            attempt_count=case.attempt_count,
            last_contact_at=case.last_contact_at,
            now=DECISION_NOW,
        )
    )


def test_toctou_opt_out_blocks_payment_link():
    case = _case()
    customer = _customer()
    sub = _sub()
    planning = _plan(case, customer, sub)
    assert ActionType.SEND_PAYMENT_LINK in planning.allowed_actions
    opted = _customer(customer_opted_out=True)
    result = ActionValidator().validate(
        case=case,
        customer=opted,
        subscription=sub,
        action=ActionType.SEND_PAYMENT_LINK,
        planning_decision=planning,
        budget_remaining=5,
    )
    assert result.ok is False
    assert result.stop_reason is StopReason.CUSTOMER_OPTED_OUT
    assert ActionType.SEND_PAYMENT_LINK in result.execution_decision.blocked_actions


def test_dispute_stops_and_escalates():
    case = _case()
    customer = _customer(has_active_dispute=True)
    sub = _sub()
    planning = _plan(case, customer, sub)
    result = ActionValidator().validate(
        case=case,
        customer=customer,
        subscription=sub,
        action=ActionType.SEND_PAYMENT_LINK,
        planning_decision=planning,
        budget_remaining=5,
    )
    assert result.ok is False
    assert result.stop_reason is StopReason.ACTIVE_DISPUTE
    assert result.escalate is True


def test_closed_case_cannot_execute():
    case = _case(status=RecoveryCaseStatus.CLOSED)
    customer = _customer()
    sub = _sub()
    planning = _plan(case, customer, sub)
    result = ActionValidator().validate(
        case=case,
        customer=customer,
        subscription=sub,
        action=ActionType.SEND_PAYMENT_LINK,
        planning_decision=planning,
        budget_remaining=5,
    )
    assert result.stop_reason is StopReason.CASE_CLOSED


def test_max_attempts_blocks_fourth():
    case = _case(attempt_count=3)
    customer = _customer()
    sub = _sub()
    planning = _plan(case, customer, sub)
    result = ActionValidator().validate(
        case=case,
        customer=customer,
        subscription=sub,
        action=ActionType.SEND_PAYMENT_LINK,
        planning_decision=planning,
        budget_remaining=5,
    )
    assert result.stop_reason is StopReason.MAX_ATTEMPTS_REACHED


def test_budget_exhausted_blocks_consuming_action():
    case = _case()
    customer = _customer()
    sub = _sub()
    planning = _plan(case, customer, sub)
    result = ActionValidator().validate(
        case=case,
        customer=customer,
        subscription=sub,
        action=ActionType.SEND_PAYMENT_LINK,
        planning_decision=planning,
        budget_remaining=0,
    )
    assert result.stop_reason is StopReason.BUDGET_EXHAUSTED


def test_zero_ev_stops_only_when_model_estimate_exists():
    case = _case()
    customer = _customer()
    policy = _plan(case, customer, _sub())
    assert (
        stop_before_action(
            case=case,
            customer=customer,
            decision=policy,
            recommended=ActionType.SEND_PAYMENT_LINK,
            incremental_ev_paise=0,
            max_attempts=3,
            hard_cap=4,
            budget_remaining=5,
        )
        is StopReason.NEGATIVE_OR_ZERO_EV
    )
    assert (
        stop_before_action(
            case=case,
            customer=customer,
            decision=policy,
            recommended=ActionType.SEND_PAYMENT_LINK,
            incremental_ev_paise=None,
            max_attempts=3,
            hard_cap=4,
            budget_remaining=5,
        )
        is None
    )
