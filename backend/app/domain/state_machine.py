"""Subscription state machine.

Pure: no I/O, no clock, no database. Given a current status and an event type
it returns what should happen. This is the layer that must never live inside a
route handler, because it is the part a reviewer needs to be able to read in
one sitting and check by eye.
"""

from dataclasses import dataclass
from enum import StrEnum

from app.domain.enums import LIFECYCLE_EVENTS, EventType, ReasonCode, SubscriptionStatus

ACTIVE = SubscriptionStatus.ACTIVE
PENDING = SubscriptionStatus.PENDING
HALTED = SubscriptionStatus.HALTED


class Decision(StrEnum):
    TRANSITION = "transition"
    NO_OP = "no_op"
    REJECTED = "rejected"


@dataclass(frozen=True)
class TransitionOutcome:
    decision: Decision
    from_status: SubscriptionStatus
    to_status: SubscriptionStatus | None
    reason_code: ReasonCode
    opens_halt_episode: bool = False
    closes_halt_episode: bool = False


#: The complete set of permitted lifecycle transitions.
#:
#: ACTIVE -> HALTED is deliberately absent. In the modelled lifecycle a
#: subscription reaches HALTED only after retries fail, so it must pass through
#: PENDING. Accepting a direct halt would let a dropped `subscription.pending`
#: event silently produce a halt episode with no recorded cause.
#:
#: HALTED -> PENDING is deliberately absent: leaving a halt is a reactivation,
#: and allowing a quiet slide back to PENDING would close a halt episode
#: without a reactivation to attribute it to.
TRANSITION_TABLE: dict[tuple[SubscriptionStatus, EventType], SubscriptionStatus] = {
    (ACTIVE, EventType.SUBSCRIPTION_PENDING): PENDING,
    (PENDING, EventType.SUBSCRIPTION_HALTED): HALTED,
    # Payment recovered before the retry window expired — no halt episode.
    (PENDING, EventType.SUBSCRIPTION_ACTIVATED): ACTIVE,
    # The transition RECLAIM exists for.
    (HALTED, EventType.SUBSCRIPTION_ACTIVATED): ACTIVE,
}

#: The status each lifecycle event asserts the subscription is now in. Used to
#: detect a redelivery that asserts the state we are already in.
EVENT_TARGET_STATUS: dict[EventType, SubscriptionStatus] = {
    EventType.SUBSCRIPTION_PENDING: PENDING,
    EventType.SUBSCRIPTION_HALTED: HALTED,
    EventType.SUBSCRIPTION_ACTIVATED: ACTIVE,
}


def is_lifecycle_event(event_type: EventType) -> bool:
    return event_type in LIFECYCLE_EVENTS


def evaluate(current: SubscriptionStatus, event_type: EventType) -> TransitionOutcome:
    """Decide what a lifecycle event does to a subscription in `current`."""
    if not is_lifecycle_event(event_type):
        raise ValueError(f"{event_type} is not a lifecycle event")

    target = EVENT_TARGET_STATUS[event_type]

    # A redelivery with a fresh event_id asserting the state we are already in.
    # Treated as a no-op rather than an error: at-least-once delivery makes this
    # normal, and failing it would turn routine webhook behaviour into noise.
    if target == current:
        return TransitionOutcome(
            decision=Decision.NO_OP,
            from_status=current,
            to_status=current,
            reason_code=ReasonCode.NO_OP_SAME_STATE,
        )

    to_status = TRANSITION_TABLE.get((current, event_type))
    if to_status is None:
        return TransitionOutcome(
            decision=Decision.REJECTED,
            from_status=current,
            to_status=None,
            reason_code=ReasonCode.ILLEGAL_TRANSITION,
        )

    return TransitionOutcome(
        decision=Decision.TRANSITION,
        from_status=current,
        to_status=to_status,
        reason_code=ReasonCode.OK,
        opens_halt_episode=(to_status == HALTED),
        closes_halt_episode=(current == HALTED and to_status == ACTIVE),
    )
