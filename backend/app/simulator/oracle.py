"""Synthetic outcome oracle.

The oracle knows a case, an action, and a run seed. It does not know which
strategy asked. Asking twice with the same triple returns the same answer.

Hidden `latent_payment_intent` is derived from (seed, customer_id) and is
never written onto a recovery case. Strategies cannot see it because they
never receive this module's internals.

Assumptions are documented in docs/evaluation.md. They were not tuned to
produce a target ROC-AUC.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from random import Random

from app.domain.enums import ActionType


def _stream(*parts: object) -> Random:
    material = "|".join(str(p) for p in parts).encode("utf-8")
    digest = hashlib.sha256(material).hexdigest()
    return Random(int(digest[:16], 16))


def latent_payment_intent(run_seed: int, customer_id: str) -> float:
    """Hidden trait in [0, 1]. Not an input to any strategy."""
    return round(_stream(run_seed, "latent", customer_id).random(), 6)


def _clip(value: float) -> float:
    return max(0.0, min(1.0, value))


def recovery_probability(
    action: ActionType,
    *,
    latent: float,
    historical_success: float,
    has_dispute: bool,
    opted_out: bool,
) -> float:
    if action is ActionType.ESCALATE_TO_MERCHANT:
        return 0.0
    if has_dispute and action is not ActionType.NO_ACTION:
        return 0.0
    if opted_out and action is ActionType.SEND_PAYMENT_LINK:
        return _clip(0.04 * latent)

    base = 0.07 + 0.38 * latent + 0.18 * historical_success
    if action is ActionType.NO_ACTION:
        return _clip(base * 0.50)
    if action is ActionType.SEND_PAYMENT_LINK:
        return _clip(base + 0.16)
    if action is ActionType.ATTEMPT_MANUAL_CHARGE:
        return _clip(base + 0.20)
    return 0.0


@dataclass(frozen=True)
class OracleOutcome:
    outcome: str
    amount_recovered_paise: int
    synthetic: bool = True


@dataclass(frozen=True)
class OracleCase:
    """What the oracle is allowed to see. No strategy name."""

    case_id: str
    customer_id: str
    backlog_amount_paise: int
    historical_payment_success_rate: float
    has_dispute: bool
    customer_opted_out: bool


class OutcomeOracle:
    def __init__(self, run_seed: int) -> None:
        self.run_seed = run_seed

    def decide(self, case: OracleCase, action: ActionType) -> OracleOutcome:
        rng = _stream(self.run_seed, case.case_id, action.value)
        latent = latent_payment_intent(self.run_seed, case.customer_id)
        p = recovery_probability(
            action,
            latent=latent,
            historical_success=case.historical_payment_success_rate,
            has_dispute=case.has_dispute,
            opted_out=case.customer_opted_out,
        )
        if action is ActionType.ESCALATE_TO_MERCHANT:
            return OracleOutcome("escalated", 0)
        draw = rng.random()
        if draw < p:
            return OracleOutcome("paid", case.backlog_amount_paise)
        if action is ActionType.SEND_PAYMENT_LINK and draw < p + 0.08:
            return OracleOutcome("pending", 0)
        return OracleOutcome("failed", 0)
