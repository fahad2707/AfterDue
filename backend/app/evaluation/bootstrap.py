"""Bootstrap intervals on case-level contributions. No significance claims."""

from dataclasses import dataclass
from random import Random

from app.evaluation.metrics import CaseContribution


@dataclass(frozen=True)
class Interval:
    point: int
    low: int
    high: int
    samples: int
    level: float = 0.95


def _percentile(sorted_values: list[int], q: float) -> int:
    if not sorted_values:
        return 0
    idx = min(len(sorted_values) - 1, max(0, int(round(q * (len(sorted_values) - 1)))))
    return sorted_values[idx]


def interval_for(
    contribs: list[CaseContribution],
    *,
    field: str,
    samples: int,
    seed: int,
) -> Interval:
    rng = Random(seed)
    n = len(contribs)
    point = sum(getattr(row, field) for row in contribs)
    if n == 0 or samples < 1:
        return Interval(point=point, low=point, high=point, samples=0)
    draws: list[int] = []
    for _ in range(samples):
        total = 0
        for _i in range(n):
            total += getattr(contribs[rng.randrange(n)], field)
        draws.append(total)
    draws.sort()
    return Interval(
        point=point,
        low=_percentile(draws, 0.025),
        high=_percentile(draws, 0.975),
        samples=samples,
    )
