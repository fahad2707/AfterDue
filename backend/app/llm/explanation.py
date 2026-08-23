from app.llm.deterministic import answer as deterministic_answer
from app.llm.deterministic import explain as deterministic_explain
from app.llm.deterministic import extract_without_model
from app.llm.grounding import explanation_is_grounded, extraction_is_supported
from app.llm.prompts import (
    SYSTEM_EXPLANATION,
    SYSTEM_EXTRACT,
    SYSTEM_QA,
    explanation_user,
    extract_user,
    qa_user,
)
from app.llm.provider import LanguageProvider, LanguageUnavailable
from app.llm.schemas import CaseExplanation, ExtractionProposal, QAAnswer


class CaseExplanationService:
    def __init__(self, provider: LanguageProvider | None = None) -> None:
        self.provider = provider

    def explain(self, facts: dict, *, prefer_llm: bool = False) -> tuple[CaseExplanation, str]:
        fallback = deterministic_explain(facts)
        if not prefer_llm or self.provider is None:
            return fallback, "deterministic"
        try:
            generated = self.provider.generate_structured(
                system=SYSTEM_EXPLANATION,
                user=explanation_user(facts),
                schema=CaseExplanation,
            )
        except LanguageUnavailable:
            return fallback, "deterministic"
        if not explanation_is_grounded(generated, facts):
            return fallback, "deterministic"
        return generated, "llm"

    def ask(self, question: str, facts: dict, *, prefer_llm: bool = False) -> tuple[QAAnswer, str]:
        fallback = deterministic_answer(question, facts)
        if not prefer_llm or self.provider is None:
            return fallback, "deterministic"
        try:
            generated = self.provider.generate_structured(
                system=SYSTEM_QA,
                user=qa_user(question, facts),
                schema=QAAnswer,
            )
        except LanguageUnavailable:
            return fallback, "deterministic"
        if generated.insufficient_information and not generated.answer:
            generated.answer = (
                "The audit trail does not contain enough information to determine that."
            )
        return generated, "llm"

    def extract(
        self, source_text: str, *, prefer_llm: bool = False
    ) -> tuple[ExtractionProposal, str]:
        fallback = extract_without_model(source_text)
        if not prefer_llm or self.provider is None:
            if not extraction_is_supported(fallback, source_text):
                return ExtractionProposal(
                    uncertainty_note="No supported evidence found in the source text."
                ), "deterministic"
            return fallback, "deterministic"
        try:
            generated = self.provider.generate_structured(
                system=SYSTEM_EXTRACT,
                user=extract_user(source_text),
                schema=ExtractionProposal,
            )
        except LanguageUnavailable:
            return fallback, "deterministic"
        if not extraction_is_supported(generated, source_text):
            return ExtractionProposal(
                uncertainty_note="Extracted facts were not supported by a source span."
            ), "deterministic"
        return generated, "llm"
