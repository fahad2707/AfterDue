from pydantic import BaseModel


class PlanRequest(BaseModel):
    prefer_llm: bool = False


class ExecuteRequest(BaseModel):
    prefer_llm: bool = False
    idempotency_key: str | None = None


class AskRequest(BaseModel):
    question: str
    prefer_llm: bool = False


class ExtractRequest(BaseModel):
    source_text: str
    apply: bool = False
    prefer_llm: bool = False
