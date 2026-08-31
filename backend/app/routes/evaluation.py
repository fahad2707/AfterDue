from fastapi import APIRouter, HTTPException, status

from app.evaluation.benchmark import report_to_dict, run_benchmark
from app.evaluation.config import EvaluationConfig
from app.ml.errors import ModelUnavailable
from app.schemas.evaluation import EvaluationRequest, EvaluationRunResponse

router = APIRouter(prefix="/api/evaluation", tags=["evaluation"])


@router.post("/run", response_model=EvaluationRunResponse)
def run_evaluation(body: EvaluationRequest):
    try:
        report = run_benchmark(EvaluationConfig.model_validate(body.model_dump()))
    except ModelUnavailable as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, str(exc)) from exc
    return report_to_dict(report)
