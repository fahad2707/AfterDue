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
7. Read historical unpaid, collectible receivables, review required,
   excluded, budget, recovered, yield (recovered / collectible eligible).
8. Open Recovery cases. Queue is ranked by expected incremental recovery
   when a model analysis exists; otherwise by collectible amount — not raw
   historical unpaid.
9. Open one case. Confirm lifecycle, per-invoice service delivery and
   collectibility, Collectibility panel before Policy, then Model, audit.
10. Open `/policy`. Confirm deterministic rules and documented vs assumed provenance.
11. Open `/evaluation`. Run the 1,000-subscriber benchmark (seed 42). Read
    whether Naive targeted invalid debt, and the diagnostics if strategies tie.

Every rupee figure on Overview/Cases comes from the selected simulation run.
Evaluation is a separate in-memory benchmark and does not write Mongo.


## M6 — agent trace (after M5 model + a generated run)

11. Open a recovery case. Confirm **RECLAIM recommendation** (action,
    expected incremental recovery, estimated intervention lift).
12. Read **Why this action?** after **Plan (no execution)**. This is
    deterministic. Do **not** expect a Claude call on page load.
13. Optionally click **Generate AI explanation**. If the key is missing,
    the same deterministic copy is shown and the source says so.
14. Confirm the banner **SIMULATED — NO REAL PAYMENT WILL BE ATTEMPTED**.
15. Click **Run simulated recovery**. Watch the trace:

    Observed case → Policy checked → Model analyzed → Action proposed →
    Policy revalidated → Action executed (or blocked) → Outcome observed →
    Stopped / closed / escalated.

16. Use **Ask RECLAIM about this decision** chips. If the audit cannot
    answer, the copy says the record does not contain enough information.
17. Optional TOCTOU demo (API or Compass): plan a payment link, set
    `customer_opted_out`, execute — validator blocks, no budget claim,
    no oracle outcome.

Claude is never part of Naive / Rule-based / RECLAIM rupee totals.
Leave `LLM_ENABLED=false` for the measured comparison.
