"""Single feature builder for training and inference.

Hidden oracle state is structurally excluded: the input is a CaseView plus
an action, and CaseView does not carry latent intent or outcomes.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Any

import pandas as pd

from app.domain.enums import ActionType
from app.simulator.strategies import CaseView

FEATURE_VERSION = "v1"

NUMERIC_FEATURES: tuple[str, ...] = (
    "backlog_amount_paise",
    "invoice_count",
    "halt_duration_days",
    "days_since_reactivation",
    "historical_payment_success_rate",
    "previous_failure_count",
    "previous_halt_count",
    "subscription_age_days",
    "plan_amount_paise",
    "risk_flag_count",
    "mandate_max_amount_paise",
    "has_dispute",
    "customer_opted_out",
)

CATEGORICAL_FEATURES: tuple[str, ...] = (
    "card_type",
    "action",
)

FEATURE_NAMES: tuple[str, ...] = NUMERIC_FEATURES + CATEGORICAL_FEATURES

FORBIDDEN_FEATURE_TOKENS: frozenset[str] = frozenset(
    {
        "latent",
        "latent_payment_intent",
        "oracle",
        "outcome",
        "amount_recovered",
        "counterfactual",
        "strategy",
    }
)


def feature_schema_hash(names: tuple[str, ...] = FEATURE_NAMES) -> str:
    material = f"{FEATURE_VERSION}|{','.join(names)}".encode()
    return hashlib.sha256(material).hexdigest()


@dataclass(frozen=True)
class FeatureRow:
    values: dict[str, Any]
    feature_names: tuple[str, ...]
    schema_hash: str
    version: str = FEATURE_VERSION

    def to_frame(self) -> pd.DataFrame:
        return pd.DataFrame([{name: self.values[name] for name in self.feature_names}])


def build_features(view: CaseView, action: ActionType) -> FeatureRow:
    """Decision-time features only. Same function for train and serve."""
    values: dict[str, Any] = {
        "backlog_amount_paise": int(view.backlog_amount_paise),
        "invoice_count": int(view.invoice_count),
        "halt_duration_days": int(view.halt_duration_days),
        "days_since_reactivation": int(view.days_since_reactivation),
        "historical_payment_success_rate": float(view.historical_payment_success_rate),
        "previous_failure_count": int(view.previous_failure_count),
        "previous_halt_count": int(view.previous_halt_count),
        "subscription_age_days": int(view.subscription_age_days),
        "plan_amount_paise": int(view.plan_amount_paise),
        "risk_flag_count": len(view.risk_flags),
        "mandate_max_amount_paise": int(view.mandate_max_amount_paise),
        "has_dispute": int(view.has_dispute),
        "customer_opted_out": int(view.customer_opted_out),
        "card_type": view.card_type,
        "action": action.value,
    }
    leaked = FORBIDDEN_FEATURE_TOKENS.intersection(values)
    if leaked:
        raise RuntimeError(f"forbidden feature tokens present: {sorted(leaked)}")
    return FeatureRow(
        values=values,
        feature_names=FEATURE_NAMES,
        schema_hash=feature_schema_hash(),
    )


def rows_to_frame(rows: list[FeatureRow]) -> pd.DataFrame:
    if not rows:
        return pd.DataFrame(columns=list(FEATURE_NAMES))
    return pd.DataFrame([{k: row.values[k] for k in FEATURE_NAMES} for row in rows])
