# RECLAIM — Synthetic evaluation (M3)

This document is the contract for the experimental laboratory. Every number
the simulator produces is synthetic. **SYNTHETIC SIMULATION — NOT PRODUCTION
DATA.** These are not Razorpay production distributions.

## Why a simulator

We cannot run a randomised recovery experiment on live subscribers. A seeded
synthetic world lets every strategy see the same customers, the same halt
episodes, the same policy constraints, the same intervention budget, and the
same outcome-generating process. Only the decision rule changes.

## What is generated

For each subscriber the population draw (`simulator/population.py`) assigns:

| Variable | Role |
|---|---|
| plan amount | Discrete ladder ₹499–₹19,999, clipped to config |
| card type | Bernoulli(`domestic_card_ratio`) |
| risk / dispute / opt-out | Independent Bernoulli rates |
| fate | always active / halted never returned / reactivated |
| missed cycles | Uniform `min_missed_cycles`..`max_missed_cycles` |
| second halt episode | 8% of reactivated subscribers |
| historical payment success | Uniform-ish 0.35–0.95, observable |
| previous failures / age | Observable integers |
| `latent_payment_intent` | Hidden in [0, 1], derived from `(seed, customer_id)` |

Default rates (config knobs, not claimed as real):

- halt_rate 0.45
- reactivation_rate 0.65
- domestic_card_ratio 0.75
- risk_flag_rate 0.08
- dispute_rate 0.03
- opt_out_rate 0.04

Only `HALTED → ACTIVE` with unpaid invoices becomes a recovery case. That
path goes through the real event ingest, state machine, backlog builder, and
policy engine.

## Observable vs hidden

Strategies may see everything on `CaseView`: backlog, invoice count, halt
duration, recency, card type, risk flags, historical success, prior failures,
age, and the policy-allowed action set.

They must not see `latent_payment_intent`, future outcomes, or another
strategy's name. The oracle is the only consumer of the latent. It is not
stored on the recovery case.

## Intervention budget

`intervention_budget` is a count of automated interventions.

- `send_payment_link` and `attempt_manual_charge` each consume one slot.
- `no_action` consumes nothing.
- `escalate_to_merchant` consumes nothing. Escalation is operational work,
  not an automated contact slot. Documented here so it is not silent.

Without a budget every strategy can contact everyone and ranking is decorative.

## Action costs (simulation assumptions)

Integer paise. Not Razorpay prices.

| Action | Cost |
|---|---|
| `no_action` | 0 |
| `send_payment_link` | 200 (₹2) |
| `attempt_manual_charge` | 500 (₹5) |
| `escalate_to_merchant` | 5,000 (₹50) |

## Oracle

Given `(run_seed, case_id, action)` the oracle returns a deterministic
`paid | failed | pending | escalated` outcome and an integer
`amount_recovered_paise`.

Conceptual recovery probability (clipped to [0, 1]):

```
base = 0.07 + 0.38 × latent + 0.18 × historical_success
P(no_action)            = 0.50 × base
P(send_payment_link)    = base + 0.16   (near-zero if opted out)
P(attempt_manual_charge)= base + 0.20
P(escalate)             = 0
dispute + any contact   = 0
```

A draw `u ~ hash(seed, case_id, action)` decides the realisation. Payment
links have a thin `pending` band above the paid threshold. The formula was
not tuned toward a target ROC-AUC.

The oracle does not know the strategy name. Counterfactual calls are pure:
asking what `no_action` would have done does not mutate the case.

## Baselines

### Naive

**Sees:** `CaseView` only.

**Order:** `case_id` ascending.

**Action:** first allowed of `send_payment_link`, `attempt_manual_charge`;
else escalate if policy requires it; else `no_action`.

**Budget:** stop spending automated slots once the budget is exhausted;
remaining cases get escalate/no_action.

### Rule-based

**Sees:** `CaseView` only. No oracle, no latent.

**Score:**

```
score = 1 × backlog_amount_paise
      + 50_000 if days_since_reactivation ≤ 45
      + 100_000 × historical_payment_success_rate
```

**Order:** score descending, `case_id` ascending for ties.

**Action and budget:** same rule as naive, applied to the ranked list.

## Metrics

Per strategy, all money integer paise except `recovery_yield` (a ratio):

- revenue at risk, recovered, yield
- interventions used, failed interventions, escalations, no-actions
- revenue per intervention, revenue per 100 cases
- **unnecessary interventions:** budget-consuming action whose `no_action`
  counterfactual also recovered. Synthetic causal metric. Not observable in
  production.
- **incremental revenue:** Σ (recovered | chosen action − recovered | no_action).
  Oracle ground truth, not an ML prediction.

## Limitations

- Distributions are invented for a demo, not fitted to Razorpay traffic.
- The oracle is a toy. A later model that saw the latent would cheat; we
  keep the latent out of `CaseView` so that cheat is structurally hard.
- Two `generate` calls with the same seed create different `run_id`s but
  the same world counts and the same relative features. Oracle draws are
  keyed by `case_id`, which embeds `run_id`, so outcomes are compared by
  re-running strategies on one run, not by comparing two generates.
- Rule-based may beat naive. That is allowed. We do not weaken it.
