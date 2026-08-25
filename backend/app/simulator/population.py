"""Pure population draw. No I/O. Same config + seed → same plans."""

from dataclasses import dataclass
from enum import StrEnum
from random import Random

from app.domain.enums import CardType, ServiceDeliveryStatus
from app.simulator.config import PLAN_LADDER_PAISE, SimulationConfig


class Fate(StrEnum):
    ALWAYS_ACTIVE = "always_active"
    HALTED_NEVER_RETURNED = "halted_never_returned"
    REACTIVATED = "reactivated"


class ServiceDeliveryMode(StrEnum):
    """Generic merchant service-delivery modes. Not real companies.

    PRODUCT/SIMULATION ASSUMPTION — rates are knobs, not market facts.
    """

    SUSPEND_ON_HALT = "suspend_on_halt"
    CONTINUE_DURING_GRACE = "continue_during_grace"
    MIXED_OR_UNKNOWN = "mixed_or_unknown"


@dataclass(frozen=True)
class SubscriberPlan:
    index: int
    plan_amount_paise: int
    card_type: CardType
    risk_flags: tuple[str, ...]
    has_active_dispute: bool
    customer_opted_out: bool
    fate: Fate
    missed_cycles: int
    halt_cycles: int
    historical_payment_success_rate: float
    previous_failure_count: int
    previous_halt_count: int
    subscription_age_days: int
    halt_offset_days: int
    service_delivery_mode: ServiceDeliveryMode
    first_halt_delivery: tuple[ServiceDeliveryStatus, ...]
    second_halt_delivery: tuple[ServiceDeliveryStatus, ...]


def _draw_plan_amount(rng: Random, config: SimulationConfig) -> int:
    eligible = [
        p
        for p in PLAN_LADDER_PAISE
        if config.plan_amount_min_paise <= p <= config.plan_amount_max_paise
    ]
    if not eligible:
        return int(config.plan_amount_min_paise)
    return rng.choice(eligible)


def _draw_mode(rng: Random, config: SimulationConfig) -> ServiceDeliveryMode:
    roll = rng.random()
    if roll < config.suspend_on_halt_rate:
        return ServiceDeliveryMode.SUSPEND_ON_HALT
    if roll < config.suspend_on_halt_rate + config.continue_during_grace_rate:
        return ServiceDeliveryMode.CONTINUE_DURING_GRACE
    return ServiceDeliveryMode.MIXED_OR_UNKNOWN


def draw_delivery_statuses(
    rng: Random,
    mode: ServiceDeliveryMode,
    cycles: int,
    grace_cycles: int,
) -> tuple[ServiceDeliveryStatus, ...]:
    if cycles <= 0:
        return ()
    if mode is ServiceDeliveryMode.SUSPEND_ON_HALT:
        return tuple(ServiceDeliveryStatus.SUSPENDED for _ in range(cycles))
    if mode is ServiceDeliveryMode.CONTINUE_DURING_GRACE:
        return tuple(
            ServiceDeliveryStatus.DELIVERED
            if i < grace_cycles
            else ServiceDeliveryStatus.SUSPENDED
            for i in range(cycles)
        )
    # MIXED_OR_UNKNOWN: independent per cycle. Equal thirds. Simulation assumption.
    choices = (
        ServiceDeliveryStatus.DELIVERED,
        ServiceDeliveryStatus.SUSPENDED,
        ServiceDeliveryStatus.UNKNOWN,
    )
    return tuple(rng.choice(choices) for _ in range(cycles))


def collectible_cycle_count(delivery: tuple[ServiceDeliveryStatus, ...]) -> int:
    return sum(1 for status in delivery if status is ServiceDeliveryStatus.DELIVERED)


def draw_population(config: SimulationConfig) -> list[SubscriberPlan]:
    rng = Random(config.seed)
    people: list[SubscriberPlan] = []
    for index in range(config.subscriber_count):
        enters_halt = rng.random() < config.halt_rate
        returns = enters_halt and rng.random() < config.reactivation_rate
        if not enters_halt:
            fate = Fate.ALWAYS_ACTIVE
            cycles = 0
            halt_cycles = 0
        elif returns:
            fate = Fate.REACTIVATED
            cycles = rng.randint(config.min_missed_cycles, config.max_missed_cycles)
            # A small documented fraction get a second closed halt episode.
            halt_cycles = 2 if rng.random() < 0.08 else 1
        else:
            fate = Fate.HALTED_NEVER_RETURNED
            cycles = rng.randint(config.min_missed_cycles, config.max_missed_cycles)
            halt_cycles = 1

        hist = round(0.35 + 0.60 * rng.random(), 4)
        mode = _draw_mode(rng, config)
        first = draw_delivery_statuses(rng, mode, cycles, config.grace_cycles)
        second_cycles = max(1, cycles // 2) if halt_cycles == 2 else 0
        second = draw_delivery_statuses(rng, mode, second_cycles, config.grace_cycles)
        people.append(
            SubscriberPlan(
                index=index,
                plan_amount_paise=_draw_plan_amount(rng, config),
                card_type=(
                    CardType.DOMESTIC
                    if rng.random() < config.domestic_card_ratio
                    else CardType.INTERNATIONAL
                ),
                risk_flags=("chargeback",) if rng.random() < config.risk_flag_rate else (),
                has_active_dispute=rng.random() < config.dispute_rate,
                customer_opted_out=rng.random() < config.opt_out_rate,
                fate=fate,
                missed_cycles=cycles,
                halt_cycles=halt_cycles,
                historical_payment_success_rate=hist,
                previous_failure_count=rng.randint(0, 8),
                previous_halt_count=0 if fate is Fate.ALWAYS_ACTIVE else halt_cycles,
                subscription_age_days=rng.randint(90, 900),
                halt_offset_days=rng.randint(40, 240),
                service_delivery_mode=mode,
                first_halt_delivery=first,
                second_halt_delivery=second,
            )
        )
    return people
