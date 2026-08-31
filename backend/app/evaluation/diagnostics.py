"""Explain strategy ties instead of retuning the world until someone wins."""

from app.domain.enums import ActionType
from app.evaluation.metrics import StrategyBenchmark
from app.simulator.costs import consumes_budget
from app.simulator.strategies import CaseAction, CaseView


def diagnose_ties(
    *,
    results: dict[str, StrategyBenchmark],
    actions: dict[str, list[CaseAction]],
    gated_views: list[CaseView],
    budget: int,
) -> list[str]:
    notes: list[str] = []
    reclaim = results.get("reclaim")
    rule = results.get("rule_based")
    naive = results.get("naive")
    if reclaim is None or rule is None:
        return notes

    gated_ids = {v.case_id for v in gated_views}
    automatable = [
        v
        for v in gated_views
        if any(consumes_budget(a) for a in v.allowed_actions)
    ]
    if budget >= len(automatable) and automatable:
        notes.append(
            "Intervention budget is at least the number of policy-automatable "
            f"gated cases ({budget} ≥ {len(automatable)}). Ranking then has "
            "little room to differentiate."
        )

    if (
        reclaim.incremental_recovered_paise == rule.incremental_recovered_paise
        and reclaim.collectible_recovered_paise == rule.collectible_recovered_paise
    ):
        notes.append(
            "RECLAIM and Rule-based recovered the same collectible rupees on "
            "this seed. That is reported as-is; the population was not retuned."
        )
        rec_actions = {a.case_id: a.action for a in actions.get("reclaim", [])}
        rule_actions = {a.case_id: a.action for a in actions.get("rule_based", [])}
        if rec_actions == rule_actions:
            notes.append(
                "RECLAIM and Rule-based selected the identical action on every gated case."
            )
        else:
            differ = sum(
                1
                for case_id in gated_ids
                if rec_actions.get(case_id) != rule_actions.get(case_id)
            )
            notes.append(
                f"RECLAIM and Rule-based differ on {differ} gated case(s), "
                "but those differences did not change recovered collectible rupees."
            )
            notes.append(
                "Likely causes: model ranking does not change who gets a slot, "
                "or oracle outcomes did not split on the swapped cases."
            )

    if naive is not None:
        if naive.incorrectly_targeted_paise > 0:
            notes.append(
                "Naive targeted historical unpaid including excluded and "
                "review-required invoices. Collectible recovered is still "
                "capped at true collectible value."
            )
            if (
                naive.incremental_recovered_paise == rule.incremental_recovered_paise
            ):
                notes.append(
                    "Naive matched Rule-based incremental recovery despite "
                    "targeting invalid debt, because extra interventions on "
                    "non-collectible cases recovered ₹0 and the budget was "
                    "large enough to still cover gated collectible cases."
                )
        if (
            naive.incremental_recovered_paise
            == reclaim.incremental_recovered_paise
            == rule.incremental_recovered_paise
        ):
            notes.append(
                "All three deployable strategies have the same incremental "
                "recovered rupees. Inspect budget saturation, action agreement, "
                "and whether collectibility reduced Naive's effective universe "
                "enough to matter under this seed."
            )

    if reclaim.policy_violations_executed or (rule and rule.policy_violations_executed):
        notes.append("A strategy executed a policy-blocked action. That is a benchmark bug.")

    oracle = results.get("oracle")
    if oracle is not None and reclaim is not None:
        if reclaim.incremental_recovered_paise > oracle.incremental_recovered_paise:
            notes.append(
                "RECLAIM's realized incremental recovery exceeded the expected-value "
                "oracle on this seed. The oracle is not clairvoyant; it ranks on "
                "true probabilities, not on the realized draws. This is not a bug."
            )

    if not notes:
        notes.append("Strategies diverged on this seed; no tie diagnostic required.")
    return notes


def action_agreement(left: list[CaseAction], right: list[CaseAction]) -> float:
    by_r = {a.case_id: a.action for a in right}
    if not left:
        return 1.0
    matched = sum(1 for a in left if by_r.get(a.case_id) == a.action)
    return matched / len(left)


def action_mix(actions: list[CaseAction]) -> dict[str, int]:
    counts = {action.value: 0 for action in ActionType}
    for row in actions:
        counts[row.action.value] += 1
    return counts
