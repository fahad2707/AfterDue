"""RECLAIM ranking strategy. Model + policy + budget. No oracle."""

from collections.abc import Sequence

from app.domain.enums import ActionType
from app.ml.errors import ModelUnavailable
from app.ml.predict import CaseAnalysis, analyze_case
from app.ml.registry import has_active_model, load_artifact
from app.simulator.costs import consumes_budget
from app.simulator.strategies import CaseAction, CaseView


class ReclaimStrategy:
    """Highest positive incremental EV first, then the intervention budget."""

    name = "reclaim"

    def __init__(self, pipeline=None, metadata: dict | None = None) -> None:
        if pipeline is None:
            if not has_active_model():
                raise ModelUnavailable(
                    "RECLAIM requires a valid active model. "
                    "Train one with POST /api/model/train. "
                    "Refusing to fall back to a baseline."
                )
            pipeline, metadata = load_artifact()
        self.pipeline = pipeline
        self.metadata = metadata or {}

    def analyze(self, view: CaseView) -> CaseAnalysis:
        return analyze_case(view, self.pipeline, self.metadata)

    def choose_actions(
        self, cases: Sequence[CaseView], intervention_budget: int
    ) -> list[CaseAction]:
        analyses = {view.case_id: self.analyze(view) for view in cases}
        ranked = sorted(
            cases,
            key=lambda v: (
                -analyses[v.case_id].expected_incremental_recovery_paise,
                v.synthetic_case_key or v.case_id,
            ),
        )
        remaining = intervention_budget
        chosen: list[CaseAction] = []
        for view in ranked:
            analysis = analyses[view.case_id]
            action = analysis.selected_action
            if action not in view.allowed_actions:
                action = ActionType.NO_ACTION
            if consumes_budget(action) and remaining <= 0:
                action = (
                    ActionType.NO_ACTION
                    if ActionType.NO_ACTION in view.allowed_actions
                    else ActionType.NO_ACTION
                )
            if consumes_budget(action):
                remaining -= 1
            chosen.append(CaseAction(view.case_id, action))
        by_id = {c.case_id: c for c in chosen}
        return [by_id[v.case_id] for v in cases]
