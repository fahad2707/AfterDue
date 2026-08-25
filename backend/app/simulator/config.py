from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.domain.money import Paise


class SimulationConfig(BaseModel):
    """Knobs for one synthetic world. Same config + same seed = same world."""

    model_config = ConfigDict(extra="forbid")

    subscriber_count: int = Field(default=100, ge=1, le=2000)
    halt_rate: float = Field(default=0.45, ge=0.0, le=1.0)
    reactivation_rate: float = Field(default=0.65, ge=0.0, le=1.0)
    domestic_card_ratio: float = Field(default=0.75, ge=0.0, le=1.0)
    risk_flag_rate: float = Field(default=0.08, ge=0.0, le=1.0)
    dispute_rate: float = Field(default=0.03, ge=0.0, le=1.0)
    opt_out_rate: float = Field(default=0.04, ge=0.0, le=1.0)
    plan_amount_min_paise: Paise = 49900
    plan_amount_max_paise: Paise = 1999900
    min_missed_cycles: int = Field(default=1, ge=1, le=12)
    max_missed_cycles: int = Field(default=6, ge=1, le=12)
    intervention_budget: int = Field(default=25, ge=0)
    seed: int = 42
    contact_cooldown_hours: int = Field(default=24, ge=0)
    max_attempts: int = Field(default=3, ge=1)
    #: PRODUCT/SIMULATION ASSUMPTIONS — not empirical merchant frequencies.
    #: Remainder after suspend + continue is MIXED_OR_UNKNOWN.
    suspend_on_halt_rate: float = Field(default=0.30, ge=0.0, le=1.0)
    continue_during_grace_rate: float = Field(default=0.40, ge=0.0, le=1.0)
    grace_cycles: int = Field(default=6, ge=0, le=12)

    @model_validator(mode="after")
    def delivery_rates_fit(self):
        if self.suspend_on_halt_rate + self.continue_during_grace_rate > 1.0:
            raise ValueError(
                "suspend_on_halt_rate + continue_during_grace_rate must be <= 1"
            )
        return self


#: Discrete plan ladder in paise. Drawn, then clipped to the config range.
PLAN_LADDER_PAISE: tuple[int, ...] = (
    49900,
    99900,
    199900,
    299900,
    499900,
    799900,
    999900,
    1499900,
    1999900,
)
