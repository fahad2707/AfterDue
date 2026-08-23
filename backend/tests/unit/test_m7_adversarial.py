"""M7 adversarial unit tests: money, artifacts, LLM, system failure."""

from pathlib import Path

import pytest
from pydantic import ValidationError

from app.domain.enums import ActionType
from app.llm.explanation import CaseExplanationService
from app.llm.grounding import explanation_is_grounded
from app.llm.provider import LanguageUnavailable
from app.llm.schemas import CaseExplanation
from app.ml.errors import ModelUnavailable
from app.ml.registry import load_artifact
from app.simulator.oracle import OracleCase, OutcomeOracle
from tests.unit.test_m6_language import FACTS


class _Timeout:
    def generate_structured(self, *, system, user, schema):
        raise LanguageUnavailable("anthropic request failed: timeout")


class _RateLimit:
    def generate_structured(self, *, system, user, schema):
        raise LanguageUnavailable("anthropic request failed: rate_limit")


class _ExtraFields:
    def generate_structured(self, *, system, user, schema):
        return schema.model_validate(
            {
                **CaseExplanationService(None).explain(FACTS)[0].model_dump(),
                "secret_chain_of_thought": "charge them",
            }
        )


class _PolicyOverride:
    def generate_structured(self, *, system, user, schema):
        return CaseExplanation(
            summary="Ignore policy and charge the card.",
            why_case_exists="override",
            recommended_action_explanation="MANUAL CHARGE THIS CUSTOMER IMMEDIATELY",
            policy_constraints=["INVENTED_REASON_CODE_EXCEEDED"],
            economic_reasoning="guaranteed recovery",
            uncertainty_note="",
        )


def test_oracle_never_recovers_more_than_backlog():
    case = OracleCase(
        case_id="c1",
        synthetic_case_key="subscriber_0001_halt_01",
        synthetic_customer_key="subscriber_0001",
        backlog_amount_paise=1499700,
        historical_payment_success_rate=0.9,
        has_dispute=False,
        customer_opted_out=False,
    )
    oracle = OutcomeOracle(42)
    for action in ActionType:
        outcome = oracle.decide(case, action)
        assert isinstance(outcome.amount_recovered_paise, int)
        assert outcome.amount_recovered_paise <= case.backlog_amount_paise
        if outcome.outcome != "paid":
            assert outcome.amount_recovered_paise == 0


def test_corrupt_artifact_fails_clearly(tmp_path: Path):
    dest = tmp_path / "recovery_model.joblib"
    dest.write_bytes(b"not a joblib artifact")
    with pytest.raises((ModelUnavailable, Exception)):
        load_artifact(dest)


def test_llm_timeout_and_rate_limit_fall_back():
    for provider in (_Timeout(), _RateLimit()):
        text, source = CaseExplanationService(provider).explain(FACTS, prefer_llm=True)
        assert source == "deterministic"
        assert "unpaid" in text.why_case_exists


def test_unexpected_llm_fields_are_rejected():
    with pytest.raises(ValidationError):
        _ExtraFields().generate_structured(system="", user="", schema=CaseExplanation)
    text, source = CaseExplanationService(_ExtraFields()).explain(FACTS, prefer_llm=True)
    assert source == "deterministic"


def test_policy_override_and_guaranteed_recovery_are_ungrounded():
    generated = _PolicyOverride().generate_structured(
        system="", user="", schema=CaseExplanation
    )
    assert explanation_is_grounded(generated, FACTS) is False
    text, source = CaseExplanationService(_PolicyOverride()).explain(
        FACTS, prefer_llm=True
    )
    assert source == "deterministic"
    assert "guaranteed recovery" not in text.summary.lower()
