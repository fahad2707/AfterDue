"""Optional logistic-regression contributions. Never invented SHAP values."""

from __future__ import annotations

import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline


def logistic_contributions(pipeline: Pipeline, model_type: str) -> list[dict] | None:
    """Global signed coefficients after the shared preprocessor.

    Only valid for an uncalibrated logistic pipeline. Calibrated or tree
    models are omitted rather than approximated.
    """
    if model_type != "logistic_regression":
        return None
    if not isinstance(pipeline, Pipeline) or "clf" not in pipeline.named_steps:
        return None
    clf = pipeline.named_steps["clf"]
    if not isinstance(clf, LogisticRegression):
        return None
    prep = pipeline.named_steps["prep"]
    names = list(prep.get_feature_names_out())
    coefs = clf.coef_.ravel()
    if len(names) != len(coefs):
        return None
    order = np.argsort(np.abs(coefs))[::-1]
    return [
        {"feature": names[i], "coefficient": float(coefs[i])}
        for i in order[:12]
    ]
