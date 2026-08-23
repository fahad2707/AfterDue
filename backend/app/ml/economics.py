"""Uplift and incremental expected value. Integer paise out."""

from app.domain.enums import ActionType
from app.simulator.costs import cost_of


def uplift(p_action: float, p_no_action: float) -> float:
    return float(p_action) - float(p_no_action)


def incremental_ev_paise(
    backlog_amount_paise: int,
    action: ActionType,
    p_action: float,
    p_no_action: float,
) -> int:
    """backlog × uplift − cost, rounded to integer paise (half even).

    NO_ACTION is defined as 0: doing nothing has no incremental value.
    """
    if action is ActionType.NO_ACTION:
        return 0
    raw = backlog_amount_paise * uplift(p_action, p_no_action) - cost_of(action)
    return int(round(raw))
