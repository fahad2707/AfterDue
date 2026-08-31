"""Oracle reference policy. Evaluation-only. Not registered in STRATEGIES.

Uses ground-truth recovery_probability and latent intent. Strategies in
`app.simulator.strategies` must not import this module.
"""

from collections.abc import Sequence

from app.domain.enums import ActionType
from app.ml.economics import incremental_ev_paise
from app.simulator.costs import consumes_budget
from app.simulator.oracle import latent_payment_intent, recovery_probability
from app.simulator.strategies import CaseAction, CaseView


def _customer_key(view: CaseView) -> str:
    key = view.synthetic_case_key or view.case_id
    if "_halt_" in key:
        return key.rsplit("_halt_", 1)[0]
    return key


class OracleStrategy:
    """Greedy expected incremental recovery under true action probabilities."""

    name = "oracle"

    def __init__(self, run_seed: int) -> None:
        self.run_seed = run_seed

    def choose_actions(
        self, cases: Sequence[CaseView], intervention_budget: int
    ) -> list[CaseAction]:
        scored: list[tuple[int, str, CaseView, ActionType]] = []
        for view in cases:
            action, ev = self._best(view)
            scored.append((-ev, view.synthetic_case_key or view.case_id, view, action))
        scored.sort()
        remaining = intervention_budget
        chosen: dict[str, ActionType] = {}
        for _neg_ev, _key, view, action in scored:
            pick = action
            if consumes_budget(pick) and remaining <= 0:
                pick = ActionType.NO_ACTION
            if pick not in view.allowed_actions:
                pick = ActionType.NO_ACTION
            if consumes_budget(pick):
                remaining -= 1
            chosen[view.case_id] = pick
        return [CaseAction(v.case_id, chosen[v.case_id]) for v in cases]

    def _best(self, view: CaseView) -> tuple[ActionType, int]:
        latent = latent_payment_intent(self.run_seed, _customer_key(view))
        kwargs = dict(
            latent=latent,
            historical_success=view.historical_payment_success_rate,
            has_dispute=view.has_dispute,
            opted_out=view.customer_opted_out,
        )
        p_no = recovery_probability(ActionType.NO_ACTION, **kwargs)
        best_action = ActionType.NO_ACTION
        best_ev = 0
        for action in view.allowed_actions:
            if action is ActionType.NO_ACTION:
                continue
            if action is ActionType.ESCALATE_TO_MERCHANT:
                continue
            p = recovery_probability(action, **kwargs)
            ev = incremental_ev_paise(view.backlog_amount_paise, action, p, p_no)
            if ev > best_ev:
                best_ev = ev
                best_action = action
        if best_action not in view.allowed_actions:
            return ActionType.NO_ACTION, 0
        return best_action, best_ev
