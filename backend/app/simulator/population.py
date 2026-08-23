"""Pure population draw. No I/O. Same config + seed → same plans."""

from dataclasses import dataclass
from enum import StrEnum
from random import Random

from app.domain.enums import CardType
from app.simulator.config import PLAN_LADDER_PAISE, SimulationConfig


class Fate(StrEnum):
    ALWAYS_ACTIVE = "always_active"
    HALTED_NEVER_RETURNED = "halted_never_returned"
    REACTIVATED = "reactivated"


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


def _draw_plan_amount(rng: Random, config: SimulationConfig) -> int:
    eligible = [
        p
        for p in PLAN_LADDER_PAISE
        if config.plan_amount_min_paise <= p <= config.plan_amount_max_paise
    ]
    if not eligible:
        return int(config.plan_amount_min_paise)
    return rng.choice(eligible)


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
            )
        )
    return people
