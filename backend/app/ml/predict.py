"""Per-action probabilities, uplift, and incremental EV. Decision-time only."""

from __future__ import annotations

from dataclasses import dataclass

from sklearn.pipeline import Pipeline

from app.domain.enums import ActionType
from app.ml.economics import incremental_ev_paise, uplift
from app.ml.features import build_features
from app.simulator.strategies import CaseView

SCOREABLE: tuple[ActionType, ...] = (
    ActionType.NO_ACTION,
    ActionType.SEND_PAYMENT_LINK,
    ActionType.ATTEMPT_MANUAL_CHARGE,
)


@dataclass(frozen=True)
class ActionScore:
    action: ActionType
    probability: float
    estimated_uplift: float
    expected_incremental_recovery_paise: int


@dataclass(frozen=True)
class CaseAnalysis:
    p_no_action: float
    scores: tuple[ActionScore, ...]
    selected_action: ActionType
    p_selected_action: float
    estimated_uplift: float
    expected_incremental_recovery_paise: int
    estimated_recovery_no_action_paise: int
    estimated_recovery_selected_paise: int
    model_version: str
    model_type: str

    def score_for(self, action: ActionType) -> ActionScore | None:
        return next((s for s in self.scores if s.action is action), None)


def predict_probability(pipeline: Pipeline, view: CaseView, action: ActionType) -> float:
    frame = build_features(view, action).to_frame()
    return float(pipeline.predict_proba(frame)[0, 1])


def analyze_case(
    view: CaseView,
    pipeline: Pipeline,
    metadata: dict,
) -> CaseAnalysis:
    """Score policy-permitted actions only. Budget is applied later."""
    allowed = set(view.allowed_actions)
    p_no = (
        predict_probability(pipeline, view, ActionType.NO_ACTION)
        if ActionType.NO_ACTION in allowed
        else 0.0
    )
    scores: list[ActionScore] = []
    for action in SCOREABLE:
        if action not in allowed:
            continue
        p = p_no if action is ActionType.NO_ACTION else predict_probability(pipeline, view, action)
        lift = 0.0 if action is ActionType.NO_ACTION else uplift(p, p_no)
        ev = incremental_ev_paise(view.backlog_amount_paise, action, p, p_no)
        scores.append(
            ActionScore(
                action=action,
                probability=p,
                estimated_uplift=lift,
                expected_incremental_recovery_paise=ev,
            )
        )

    selected = _select_local(view, scores)
    chosen = next((s for s in scores if s.action is selected), None)
    p_sel = chosen.probability if chosen else p_no
    lift = chosen.estimated_uplift if chosen else 0.0
    ev = chosen.expected_incremental_recovery_paise if chosen else 0
    backlog = view.backlog_amount_paise
    return CaseAnalysis(
        p_no_action=p_no,
        scores=tuple(scores),
        selected_action=selected,
        p_selected_action=p_sel,
        estimated_uplift=lift,
        expected_incremental_recovery_paise=ev,
        estimated_recovery_no_action_paise=int(round(backlog * p_no)),
        estimated_recovery_selected_paise=int(round(backlog * p_sel)),
        model_version=str(metadata.get("model_version") or ""),
        model_type=str(metadata.get("model_type") or ""),
    )


def _select_local(view: CaseView, scores: list[ActionScore]) -> ActionType:
    allowed = set(view.allowed_actions)
    if view.requires_escalation or view.stop:
        if ActionType.ESCALATE_TO_MERCHANT in allowed:
            return ActionType.ESCALATE_TO_MERCHANT
        if ActionType.NO_ACTION in allowed:
            return ActionType.NO_ACTION
    positive = [
        s
        for s in scores
        if s.action is not ActionType.NO_ACTION and s.expected_incremental_recovery_paise > 0
    ]
    if not positive:
        return ActionType.NO_ACTION
    best = max(
        positive,
        key=lambda s: (s.expected_incremental_recovery_paise, s.action.value),
    )
    return best.action


def try_analyze_view(view: CaseView) -> dict | None:
    from app.ml.errors import FeatureSchemaMismatch, ModelUnavailable
    from app.ml.explain import logistic_contributions
    from app.ml.registry import has_active_model, load_artifact

    if not has_active_model():
        return None
    try:
        pipeline, metadata = load_artifact()
    except (ModelUnavailable, FeatureSchemaMismatch):
        return None
    payload = analysis_to_dict(analyze_case(view, pipeline, metadata))
    payload["feature_contributions"] = logistic_contributions(
        pipeline, str(metadata.get("model_type") or "")
    )
    return payload


def analysis_to_dict(analysis: CaseAnalysis) -> dict:
    return {
        "p_no_action": analysis.p_no_action,
        "selected_action": analysis.selected_action.value,
        "p_selected_action": analysis.p_selected_action,
        "estimated_uplift": analysis.estimated_uplift,
        "expected_incremental_recovery_paise": analysis.expected_incremental_recovery_paise,
        "estimated_recovery_no_action_paise": analysis.estimated_recovery_no_action_paise,
        "estimated_recovery_selected_paise": analysis.estimated_recovery_selected_paise,
        "model_version": analysis.model_version,
        "model_type": analysis.model_type,
        "candidates": [
            {
                "action": s.action.value,
                "probability": s.probability,
                "estimated_uplift": s.estimated_uplift,
                "expected_incremental_recovery_paise": s.expected_incremental_recovery_paise,
            }
            for s in analysis.scores
        ],
        "synthetic": True,
    }
