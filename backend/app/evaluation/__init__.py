"""Offline evaluation / benchmark layer.

Separate from the production recovery path. Strategies still do not see
oracle outcomes or latent intent. Naive is scored on ungated historical
unpaid; Rule-based and RECLAIM keep the production collectibility gate.
"""

from app.evaluation.benchmark import run_benchmark
from app.evaluation.config import EvaluationConfig

__all__ = ["EvaluationConfig", "run_benchmark"]
