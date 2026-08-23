import pytest

from app.domain.enums import EventType, ReasonCode, SubscriptionStatus
from app.domain.state_machine import (
    TRANSITION_TABLE,
    Decision,
    evaluate,
    is_lifecycle_event,
)

ACTIVE = SubscriptionStatus.ACTIVE
PENDING = SubscriptionStatus.PENDING
HALTED = SubscriptionStatus.HALTED


@pytest.mark.parametrize(
    ("current", "event", "expected"),
    [
        (ACTIVE, EventType.SUBSCRIPTION_PENDING, PENDING),
        (PENDING, EventType.SUBSCRIPTION_HALTED, HALTED),
        (PENDING, EventType.SUBSCRIPTION_ACTIVATED, ACTIVE),
        (HALTED, EventType.SUBSCRIPTION_ACTIVATED, ACTIVE),
    ],
)
def test_permitted_transitions(current, event, expected):
    outcome = evaluate(current, event)
    assert outcome.decision is Decision.TRANSITION
    assert outcome.to_status is expected
    assert outcome.reason_code is ReasonCode.OK


@pytest.mark.parametrize(
    ("current", "event"),
    [
        # A halt must be preceded by a pending state; accepting a direct halt
        # would hide a dropped subscription.pending event.
        (ACTIVE, EventType.SUBSCRIPTION_HALTED),
        # Leaving HALTED is a reactivation, never a quiet slide to PENDING.
        (HALTED, EventType.SUBSCRIPTION_PENDING),
    ],
)
def test_illegal_transitions_are_rejected(current, event):
    outcome = evaluate(current, event)
    assert outcome.decision is Decision.REJECTED
    assert outcome.reason_code is ReasonCode.ILLEGAL_TRANSITION
    assert outcome.to_status is None


@pytest.mark.parametrize(
    ("current", "event"),
    [
        (ACTIVE, EventType.SUBSCRIPTION_ACTIVATED),
        (PENDING, EventType.SUBSCRIPTION_PENDING),
        (HALTED, EventType.SUBSCRIPTION_HALTED),
    ],
)
def test_redelivery_of_current_state_is_a_no_op(current, event):
    """At-least-once delivery makes this routine, so it must not be an error."""
    outcome = evaluate(current, event)
    assert outcome.decision is Decision.NO_OP
    assert outcome.to_status is current
    assert outcome.reason_code is ReasonCode.NO_OP_SAME_STATE


def test_halt_episode_flags_are_set_only_on_the_right_edges():
    opening = evaluate(PENDING, EventType.SUBSCRIPTION_HALTED)
    assert opening.opens_halt_episode and not opening.closes_halt_episode

    closing = evaluate(HALTED, EventType.SUBSCRIPTION_ACTIVATED)
    assert closing.closes_halt_episode and not closing.opens_halt_episode

    # Recovering before the halt means there is no episode to open or close.
    recovered = evaluate(PENDING, EventType.SUBSCRIPTION_ACTIVATED)
    assert not recovered.opens_halt_episode and not recovered.closes_halt_episode


def test_opening_and_closing_never_coincide():
    """The repository writes an episode push and an episode close as one update.
    Mongo would reject a conflicting path, so this must stay impossible."""
    for (current, event) in TRANSITION_TABLE:
        outcome = evaluate(current, event)
        assert not (outcome.opens_halt_episode and outcome.closes_halt_episode)


def test_non_lifecycle_events_are_not_state_machine_input():
    assert not is_lifecycle_event(EventType.INVOICE_CREATED)
    with pytest.raises(ValueError):
        evaluate(ACTIVE, EventType.INVOICE_CREATED)
