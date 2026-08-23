# RECLAIM — Vertical demo journey (M4)

Not the final five-minute script. This is the path a reviewer can walk
without editing code.

Canonical configuration (actual simulator, not hardcoded metrics):

- subscriber_count = 100
- seed = 42
- intervention_budget = 25

Generation through the real ingest path takes a couple of minutes.

## Walkthrough

1. Open `/simulate`.
2. Confirm the synthetic warning is visible.
3. Use seed 42 (Replay same seed) and Generate synthetic world.
4. Wait for the run_id and world summary.
5. Run baselines (Naive + Rule-based).
6. Open Overview (`/`). Confirm the same `run` query parameter.
7. Read revenue at risk, case count, budget, best baseline, yield.
8. Open Recovery cases. Queue is sorted by backlog, not by a model.
9. Open one case. Confirm lifecycle, halt invoices, policy provenance, audit.
10. Open `/policy`. Confirm deterministic rules and documented vs assumed provenance.

Every rupee figure on these pages comes from the selected simulation run.
There is no AI recommendation in M4.
