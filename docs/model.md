# RECLAIM — Recovery model (M5)

> **SYNTHETIC SIMULATION — NOT PRODUCTION DATA.**
> Probabilities, lifts, and expected incremental recovery are model estimates
> trained in a randomized synthetic environment. They are not causal truth
> and not guaranteed rupees.

## Objective

The model does not answer “who will pay?”

It answers:

**Given limited recovery capacity, which permitted intervention creates the
highest expected incremental recovered revenue for this case?**

```
P(recovery | action, decision-time context)
uplift(A) = P(A) − P(NO_ACTION)
incremental_ev_paise(A) = round(backlog × uplift(A) − cost(A))
```

`NO_ACTION` incremental EV is defined as 0. If every automated intervention
has non-positive EV, RECLAIM selects `NO_ACTION` (or escalation if policy
requires it).

The LLM is outside this path.

## Features

Training and inference use one builder: `app/ml/features.py`.

| Feature | Kind |
|---|---|
| backlog_amount_paise | numeric |
| invoice_count | numeric |
| halt_duration_days | numeric |
| days_since_reactivation | numeric |
| historical_payment_success_rate | numeric |
| previous_failure_count | numeric |
| previous_halt_count | numeric |
| subscription_age_days | numeric |
| plan_amount_paise | numeric |
| risk_flag_count | numeric |
| mandate_max_amount_paise | numeric |
| has_dispute | numeric 0/1 |
| customer_opted_out | numeric 0/1 |
| card_type | categorical |
| action | categorical |

Hidden `latent_payment_intent`, oracle outcomes, counterfactuals, and
strategy names are not features. **Service delivery / collectibility is
not a feature.** Entitlement is a deterministic upstream gate; the model
only sees cases that already passed it. `backlog_amount_paise` and
`invoice_count` are collectible eligible values.

A schema hash (`sha256` of `v1|{feature names}`) is stored on the
artifact. Inference refuses to predict if the current hash differs.

The committed artifact was retrained after the collectibility gate because
the eligible case universe and backlog semantics changed, not to chase a
better benchmark. Methodology (randomized actions, grouped split, LR vs
HGB, Brier selection) is unchanged.

## Randomized action assignment

≈20,000 rows from `dataset_seed`. Each row is one synthetic reactivated
case plus **one action drawn uniformly from the policy-permitted set**
`{no_action, send_payment_link, attempt_manual_charge}`.

Assignments do **not** come from Naive or Rule-based. Randomization is
what makes action-effect estimation unconfounded in this lab.

Target: `recovered = 1` if the M3 oracle realized `paid`.

## Grouped splitting

Rows are grouped by `world_seed:synthetic_case_key`.
`GroupShuffleSplit` produces approximately 70% / 15% / 15%
train / validation / test. The same synthetic case cannot appear in two
splits. The test split is scored once after model selection.

## Models evaluated

Both sit in a sklearn `Pipeline` + `ColumnTransformer`
(`StandardScaler` on numerics, dense `OneHotEncoder` on categoricals):

- Logistic Regression
- HistGradientBoostingClassifier (`max_depth=4`)

Selection is by **validation Brier score** (probability quality), with
ROC-AUC as a tie-break. We do not pick a tree model because its AUC is
0.01 higher.

Isotonic calibration is fitted on train (`cv=3`) and kept only if it
improves validation Brier. Raw probabilities are kept otherwise.

### Selected model (dataset_seed=42, n=20,000)

**Logistic regression, uncalibrated.**

Validation Brier: logistic 0.1955 vs HistGradientBoosting 0.1967.
Calibration val Brier 0.1958 was not better, so raw probabilities were kept.
AUC was not the tie-break; Brier was.

Held-out test (grouped, unused during selection):

| Metric | Value |
|---|---|
| Precision | 0.513 |
| Recall | 0.636 |
| F1 | 0.568 |
| ROC-AUC | 0.686 |
| Brier | 0.197 |

Confusion (test): TN 1396, FP 604, FN 364, TP 636.

Calibration is only moderately aligned: low-probability bins are close,
higher bins slightly over-predict. We did not force isotonic calibration
because it did not improve validation Brier.

## Artifact and registry

`backend/app/ml/artifacts/recovery_model.joblib` plus a `.meta.json`
sidecar. Metadata includes `model_version`, `trained_at`, `dataset_seed`,
`sklearn_version`, `feature_names`, `feature_schema_hash`, `model_type`,
and the evaluation summary.

`model_runs` stores the same metadata in Mongo. No training rows.

## RECLAIM strategy

For each case: policy-allowed actions → per-action probabilities →
uplift → incremental EV → local best (or `NO_ACTION` / required
escalation). Cases are ranked by best positive incremental EV. The
intervention budget is the same count used by the baselines. Escalation
does not consume a slot.

If RECLAIM is requested and no valid artifact exists, the API returns
409. It does not silently run Rule-based.

## Limitations

- The world and oracle are synthetic. Economic “wins” are lab results.
- Uplift is a model estimate, not a causal identification result from
  production traffic.
- Features are only those a real decision-time case would have.
- There is no Claude / LLM explanation layer in M5.
