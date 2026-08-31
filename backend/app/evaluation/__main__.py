"""CLI: python -m app.evaluation --subscribers 1000 --seed 42"""

from __future__ import annotations

import argparse
import json
import sys

from app.evaluation.benchmark import report_to_dict, run_benchmark
from app.evaluation.config import EvaluationConfig


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="RECLAIM collectibility-aware recovery benchmark (synthetic)."
    )
    parser.add_argument("--subscribers", type=int, default=1000)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--budget", type=int, default=None)
    parser.add_argument("--bootstrap", type=int, default=400)
    parser.add_argument("--no-oracle", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    config = EvaluationConfig(
        subscriber_count=args.subscribers,
        seed=args.seed,
        intervention_budget=args.budget,
        bootstrap_samples=args.bootstrap,
        include_oracle=not args.no_oracle,
    )
    report = run_benchmark(config)
    payload = report_to_dict(report)
    if args.json:
        json.dump(payload, sys.stdout, indent=2)
        sys.stdout.write("\n")
        return 0
    pop = report.population
    print("SYNTHETIC SIMULATION — NOT PRODUCTION DATA")
    print(
        f"subscribers={pop.subscriber_count} cases={pop.case_count} "
        f"gated={pop.gated_case_count} seed={pop.seed} budget={pop.intervention_budget}"
    )
    print(
        f"historical=₹{pop.historical_unpaid_paise / 100:,.0f} "
        f"collectible=₹{pop.collectible_paise / 100:,.0f} "
        f"excluded=₹{pop.not_collectible_paise / 100:,.0f} "
        f"review=₹{pop.review_required_paise / 100:,.0f}"
    )
    print()
    print(
        f"{'strategy':<12} {'universe':<8} {'net ₹':>12} {'incr ₹':>12} "
        f"{'invalid ₹':>12} {'used':>6} {'regret ₹':>12}"
    )
    for name, row in report.strategies.items():
        regret = row.regret_vs_oracle_paise
        regret_s = "—" if regret is None else f"{regret / 100:,.0f}"
        print(
            f"{name:<12} {row.universe:<8} "
            f"{row.net_recovered_paise / 100:>12,.0f} "
            f"{row.incremental_recovered_paise / 100:>12,.0f} "
            f"{row.incorrectly_targeted_paise / 100:>12,.0f} "
            f"{row.interventions:>6} {regret_s:>12}"
        )
    print()
    for line in report.diagnostics:
        print(f"- {line}")
    print()
    for line in report.limitations:
        print(f"! {line}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
