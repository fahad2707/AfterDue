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
| `latent_payment_intent` | Hidden in [0, 1], derived from `(seed, synthetic_customer_key)` |

Default rates (config knobs, not claimed as real):

- halt_rate 0.45
- reactivation_rate 0.65
- domestic_card_ratio 0.75
- risk_flag_rate 0.08
- dispute_rate 0.03
- opt_out_rate 0.04

## Service delivery during halt (PRODUCT/SIMULATION ASSUMPTION)

Invoice generation does not imply service was delivered. The world generator
stamps a `service_delivery_status` on each halt-period invoice. These rates
are knobs, **not** empirical merchant frequencies. They were not chosen so
that RECLAIM looks better.

| Mode | What it generates |
|---|---|
| `SUSPEND_ON_HALT` | Every halt-period invoice is `SUSPENDED` → not collectible |
| `CONTINUE_DURING_GRACE` | Invoices in the first `grace_cycles` (default 6) are `DELIVERED`; later cycles `SUSPENDED` |
| `MIXED_OR_UNKNOWN` | Each cycle independently `DELIVERED`, `SUSPENDED`, or `UNKNOWN` with equal weight |

Default mix (remainder after the two rates is mixed):

- suspend_on_halt_rate 0.30
- continue_during_grace_rate 0.40
- grace_cycles 6

UNKNOWN fails closed to `REVIEW_REQUIRED` and never enters ML or strategy
economics. All three strategies see the same post-collectibility case set.

Only `HALTED → ACTIVE` with **collectible** unpaid invoices becomes an
economically eligible recovery case. Historical unpaid reconstruction still
runs first; collectibility is a gate after it. That path goes through the
real event ingest, state machine, backlog builder, collectibility engine,
and policy engine.

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

Given `(run_seed, synthetic_case_key, action)` the oracle returns a
deterministic `paid | failed | pending | escalated` outcome and an integer
`amount_recovered_paise`. Persistence IDs (`run_id`, `case_id`) are not
part of the draw.

Conceptual recovery probability (clipped to [0, 1]):

```
base = 0.07 + 0.38 × latent + 0.18 × historical_success
P(no_action)            = 0.50 × base
P(send_payment_link)    = base + 0.16   (near-zero if opted out)
P(attempt_manual_charge)= base + 0.20
P(escalate)             = 0
dispute + any contact   = 0
```

A draw `u ~ hash(seed, synthetic_case_key, action)` decides the realisation.
Payment links have a thin `pending` band above the paid threshold. The
formula was not tuned toward a target ROC-AUC.

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

- **revenue_at_risk_paise:** sum of collectible eligible receivables on the
  strategy universe (`backlog_amount_paise` == `collectible_amount_paise`).
  Not raw historical unpaid invoices.
- recovered, yield = recovered / collectible eligible (`revenue_at_risk_paise`)
- interventions used, failed interventions, escalations, no-actions
- revenue per intervention, revenue per 100 cases
- **unnecessary interventions:** budget-consuming action whose `no_action`
  counterfactual also recovered. Synthetic causal metric. Not observable in
  production.
- **incremental revenue:** Σ (recovered | chosen action − recovered | no_action).
  Oracle ground truth, not an ML prediction.

## Persistence identity vs simulation identity

Two independently generated runs with the same `SimulationConfig` and seed
must be the same synthetic world, including hidden traits and counterfactual
outcomes. They must also stay isolated in Mongo.

| Identity | Examples | Role |
|---|---|---|
| Persistence | `run_id`, `customer_id`, `case_id` | Unique per generate. Scopes every Mongo document. |
| Simulation | `synthetic_customer_key`, `synthetic_case_key` | Derived only from population index and halt ordinal, e.g. `subscriber_0042` / `subscriber_0042_halt_01`. |

The split exists because a database id that embeds `run_id` cannot also be
the oracle seed. If it were, regenerating the same config would silently
change every counterfactual. Strategies still emit persistence `case_id`
when they choose an action; the oracle looks up the matching synthetic key.

Same-seed generates therefore share features, latents, oracle outcomes, and
strategy metrics. Re-running strategies on one `run_id` remains identical
as well. A different seed produces a different world.

## Limitations

- Distributions are invented for a demo, not fitted to Razorpay traffic.
- The oracle is a toy. A later model that saw the latent would cheat; we
  keep the latent out of `CaseView` so that cheat is structurally hard.
- Rule-based may beat naive. That is allowed. We do not weaken it.

## Offline evaluation layer

The live simulator still compares Naive / Rule-based / RECLAIM on the
**same post-collectibility universe**. That remains the fairness contract
for ranking.

A separate in-memory benchmark (`app/evaluation`) answers a different
question: does a system without a collectibility gate waste effort on
invalid or uncertain debt?

| Strategy | Universe | Notes |
|---|---|---|
| Naive | ungated historical unpaid | Treats halt-lineage invoices as recoverable |
| Rule-based | gated collectible | Existing deterministic score, production path |
| RECLAIM | gated collectible | Existing model + EV, production path |
| Oracle | gated collectible | Expected-value policy using true `recovery_probability`. Not deployable |

Recovered rupees are always collectible-only. Naive can still *target*
excluded and review-required amounts; those show up as incorrectly
targeted, not as extra recovered revenue.

Command:

```bash
make benchmark
# or
cd backend && uv run python -m app.evaluation --subscribers 1000 --seed 42
cd backend && uv run python -m app.evaluation --subscribers 5000 --seed 42
cd backend && uv run python -m app.evaluation --subscribers 10000 --seed 42
```

UI: `/evaluation`. Budget stays the canonical 25-per-100 ratio. If
strategies tie, diagnostics explain why. The population is not retuned
until RECLAIM wins.

The expected-value oracle is not clairvoyant. Realized incremental
recovery can beat it on one seed.

## M5 — RECLAIM vs baselines


Same world, same `run_id`, same policy, same oracle, same intervention
budget. Only the decision rule changes. RECLAIM uses the recovery model
(uplift × backlog − cost) and never the oracle or latent intent.

### Pre-collectibility (historical)

Canonical experiment under the old definition (unpaid halt invoices =
eligible): `subscriber_count=100`, `seed=42`, `intervention_budget=25`.
World: 32 recovery cases, ₹7,41,880 at risk.

| Strategy | Recovered | Incremental | Yield | Used | Unnecessary | Escalations | ₹ / intervention |
|---|---:|---:|---:|---:|---:|---:|---:|
| Naive | ₹2,37,957 | ₹94,976 | 32.07% | 25 | 5 | 7 | ₹9,518 |
| Rule-based | ₹2,37,957 | ₹94,976 | 32.07% | 25 | 5 | 7 | ₹9,518 |
| RECLAIM | ₹2,38,456 | ₹95,475 | 32.14% | 25 | 5 | 7 | ₹9,538 |

Do **not** compare new totals to this table as if they were the same
experiment.

### Post-collectibility (current definition)

`revenue_at_risk_paise` is collectible eligible receivable only.

Canonical experiment: `subscriber_count=100`, `seed=42`,
`intervention_budget=25`.

Funnel: historical unpaid ₹16,71,822 · collectible ₹8,42,415 · review
₹5,67,448 · excluded ₹2,61,959. 23 collectible cases; 3 review-required
cases excluded from strategies.

| Strategy | Recovered | Incremental | Yield | Used | Unnecessary | Escalations | ₹ / intervention |
|---|---:|---:|---:|---:|---:|---:|---:|
| Naive | ₹5,53,459 | ₹2,95,483 | 65.70% | 16 | 5 | 7 | ₹34,591 |
| Rule-based | ₹5,53,459 | ₹2,95,483 | 65.70% | 16 | 5 | 7 | ₹34,591 |
| RECLAIM | ₹5,53,459 | ₹2,95,483 | 65.70% | 16 | 5 | 7 | ₹34,591 |

All three strategies received the same post-gate universe. On this seed they
tied. The simulator was not adjusted. Replay of the same `run_id` was
identical.

We do **not** require RECLAIM to beat both baselines. If it loses or ties,
that result is reported.

Yield = recovered / collectible eligible (`revenue_at_risk_paise`).

Retraining used the same methodology (randomized action assignment,
grouped split, Logistic Regression vs HistGradientBoosting, Brier
selection). Selected model: HistGradientBoosting (validation Brier 0.1926;
test Brier 0.1932; ROC-AUC 0.694). Feature schema hash unchanged. Service
delivery is not an ML feature.


