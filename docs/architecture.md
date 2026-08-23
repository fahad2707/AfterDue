# RECLAIM — Architecture

Status: approved at Phase 0. This document is the authoritative spec; it
supersedes the original project brief wherever the two disagree.

> All results are produced by a seeded synthetic environment.
> **SYNTHETIC SIMULATION — NOT PRODUCTION DATA.**

---

## 1. Approved decisions

These were reviewed and accepted before any code was written.

### D1 — Intervention budget (approved: O1)

Every simulation run carries a configurable intervention budget. All strategies
run against the **same synthetic world, the same oracle seeds, the same policy
constraints, and the same budget**.

*Why:* without a capacity constraint every strategy eventually intervenes on
every case and recovers identical revenue, which makes prioritisation
decorative and the comparison meaningless. Under a budget, ranking quality
converts directly into rupees.

### D2 — Incremental (uplift) economics (approved: O2)

The economic objective is **not** `backlog × P(recovery)`. It is:

```
incremental_ev(action) =
    backlog_amount_paise
  × [ P(recovery | action, context) − P(recovery | no_action, context) ]
  − action_cost_paise
```

There is an explicit `no_action` arm. Training-time action assignment is
**randomised**, so the estimate is unconfounded by construction rather than by
argument.

*Why:* a customer who would have paid anyway yields nothing from an
intervention. Without a `no_action` counterfactual, "unnecessary interventions"
cannot be computed at all.

**UI constraint:** the judge-facing surface must not use causal-inference
vocabulary. It displays:

| Displayed label | Underlying quantity |
|---|---|
| Backlog | `backlog_amount_paise` |
| Estimated recovery without intervention | `P(recovery \| no_action) × backlog` |
| Estimated recovery with <action> | `P(recovery \| action) × backlog` |
| Estimated intervention lift | the probability difference |
| Expected incremental recovery | `incremental_ev(action)` |

### D3 — Mandate cap rule (approved: O3, conditionally)

`subscriptions.mandate_max_amount_paise` exists, and the policy engine blocks
`attempt_manual_charge` when the backlog exceeds it, with reason code
`MANDATE_CAP_EXCEEDED`.

**Provenance is `PRODUCT_DESIGN_ASSUMPTION`, not `DOCUMENTED_PLATFORM_BEHAVIOR`,**
until the exact Razorpay behaviour is independently verified. The provenance
field is rendered in the UI so the distinction is visible to a judge rather
than buried in a README.

### D4 — LLM off the measured path (approved: O4)

The reproducible economic decision path is entirely deterministic:

```
Recovery Case → Feature Builder → Per-action Recovery/Uplift Model
→ Incremental Expected Value → Policy Engine → Action Ranking
→ Validator → Simulated Execution → Outcome → Metrics
```

The LLM is a **separate language-intelligence layer** used only for:

1. unstructured context extraction
2. human-readable rationale
3. audit Q&A

**Hard requirement:** the economic comparison must run to completion with
`LLM_ENABLED=false`, and the core agent must stay functional when Anthropic is
unavailable. This is enforced by test, not by intention.

### D5 — Dataset size and money representation (approved: O5)

~20,000 seeded synthetic training examples. Growing the dataset requires a
learning-curve experiment showing meaningful improvement first.

**All monetary amounts are integer paise.** No floats anywhere in the money
path.

### D6 — Halt episodes (approved: N3)

`halted_at` / `reactivated_at` scalars are replaced by:

```jsonc
"halt_episodes": [
  { "episode_id": "he_1", "halted_at": "…", "reactivated_at": "…", "invoice_ids": [...] }
]
```

Each recovery case references exactly one `halt_episode_id`.
`ACTIVE → HALTED → ACTIVE → HALTED → ACTIVE` must attribute each backlog to the
correct episode.

### D7 — Simulator honesty (user modification)

The simulator is designed from transparent behavioural assumptions and latent
uncertainty. **It is not tuned to hit a target ROC-AUC, and it is not
engineered so that RECLAIM wins.** Whatever performance naturally results is
reported as-is. If RECLAIM fails to beat a baseline, we diagnose the model or
the strategy — we do not adjust the world.

### D8 — Also approved

pymongo `AsyncMongoClient` (Motor is EOL) · shared train/serve feature builder ·
logistic-regression baseline with HistGradientBoosting challenger ·
schema-hashed model artifacts · committed default artifact ·
`run_id` isolation · sequenced append-only audit logs ·
idempotency via unique indexes and upserts ·
policy → validator → executor re-check defence in depth ·
Next.js server-side proxy with server-only API URL · structured logs ·
seeded simulation · paired counterfactual oracle ·
vertical demo spine before advanced ML · real incident logging.

---

## 2. Why each safeguard exists

Short answers, kept here so the reasoning survives the build.

**`run_id`** — a judge who clicks "Run Simulation" three times must not see
three runs summed into one number. Every case, action, audit line and metric is
scoped to a run, and the dashboard renders exactly one.

**Idempotency** — payment webhooks are delivered at least once. A duplicated
`subscription.activated` must not create a second recovery case or a second
charge attempt. Enforced by a unique index on `event_id` plus upserts, never
read-then-write, because two concurrent handlers can both pass an existence
check.

**Uplift** — measures the value an intervention *adds*. Prioritising by
`P(recovery)` alone ranks customers who would have paid anyway at the top.

**Calibration** — the probability gets multiplied by money, so being right
*on average at each probability level* matters more than ranking accuracy.
A model with great AUC and bad calibration produces confident nonsense rupee
figures.

**Halt episodes** — repeat halts are normal. Scalar `halted_at` overwrites the
previous halt and misattributes the backlog.

**Policy revalidation at execution** — a dispute can arrive between analysis and
execution. Checking policy only at planning time leaves a time-of-check /
time-of-use gap in a financial action.

**Schema hashes** — a model artifact trained on a different feature set will
still happily produce a number. Asserting the feature-schema hash at inference
turns silent mispredictions into a loud failure.

**Counterfactual baselines** — seeding outcomes by
`hash(run_seed, case_id, action)` makes the comparison *paired*: the same case
under different strategies shares its randomness. This removes most of the
variance from the comparison and is what makes the `no_action` arm — and
therefore "unnecessary interventions" — computable.

---

## 3. Repository layout

```
Reclaim/
├── backend/     FastAPI + deterministic core + ML + simulator
├── frontend/    Next.js console (server-side proxy to backend)
└── docs/        architecture · product · model · policy · evaluation · incidents · demo-script
```

---

## 4. Milestones

| Milestone | Contents | Status |
|---|---|---|
| M0 | Repo, toolchain, FastAPI, `/healthz`, `/readyz`, Atlas, Next.js shell, proxy | done |
| M1 | Collections, indexes, idempotent event ingest, state machine, halt episodes, audit trail | **in review** |
| M2 | Halt episodes, backlog reconstruction, policy engine | pending |
| M3 | Seeded world, counterfactual oracle, naive / rule-based / RECLAIM strategies | pending |
| M4 | Vertical demo spine (dashboard, queue, case detail, audit timeline) | pending |
| M5 | Feature builder, uplift model, calibration, incremental EV | pending |
| M6 | LLM language layer, validator, bounded agent loop | pending |
| M7 | Adversarial tests, README, deployment, demo | pending |

---

## 5. M0 as built

**Backend** — FastAPI on Python 3.12 (uv-pinned).
`/healthz` is dependency-free liveness; `/readyz` reports each dependency and
answers 503 when any is down. `/api/*` requires the `x-internal-api-key` shared
secret whenever one is configured; health endpoints are exempt so the platform
healthcheck works. Logs are structured JSON via structlog.

**Frontend (M0)** — Next.js 16 App Router, TypeScript, Tailwind 4.
Server Components call FastAPI directly through `lib/server-api.ts`. Client
Components call same-origin `/api/*`, which `app/api/[...proxy]/route.ts`
forwards to FastAPI with the shared secret attached. The backend origin and the
secret never enter the browser bundle, and CORS is not a browser-side failure
mode.

---

## 6. M1 — ledger and event engine

M1 builds the persistent record: what happened to a subscription, when, and
what money was left unpaid as a result. It deliberately makes no decisions.

### 6.1 Idempotency

Payment webhooks are delivered at least once. Redelivery must never produce a
second state transition or a second charge attempt.

The unique index on `events.event_id` **is** the mechanism. Ingestion *claims*
an event by inserting it:

```python
try:
    await col.insert_one(event.model_dump())
    return True          # this caller owns processing
except DuplicateKeyError:
    return False         # someone already has it
```

Two concurrent deliveries both attempt the insert; exactly one succeeds. This
is why the code does not check-then-insert: between the check and the insert
another worker can pass the same check, and the result is a double transition.

**Ordering is load-bearing.** The claim happens before any mutation, so a
duplicate reaches nothing that writes. The only thing a duplicate does write is
a single `EVENT_DUPLICATE` audit line — the original effects are never
repeated, but a retry storm stays visible to an auditor.

**Known limitation.** A process crash between the successful claim and the
state update leaves the event at `processing_status: received` and it will not
be retried, because a redelivery now loses the claim. This is at-most-once
processing after a successful claim. A sweeper for stuck `received` events is
deferred; the trade was made knowingly, in favour of never double-charging.

### 6.2 Out-of-order events

Strategy chosen: **compare `occurred_at` against `last_state_change_at`**.

A lifecycle event whose logical time is strictly older than the last accepted
state change is refused with `STALE_EVENT`. It is still persisted and audited,
so nothing is silently dropped — we simply decline to let receive order
overwrite logical order.

Equal timestamps are *not* stale. Treating simultaneity as staleness would
arbitrarily discard one of two events sharing a millisecond.

`last_state_change_at` is `None` until the first transition. Creating a
subscription *sets* its state rather than *changing* it, so there is nothing
for the first event to contradict — seeding the field from `created_at` made
every historical replay fail (INC-007), which would have broken M2's simulator.

Why not full event-sourced replay (recompute state from the whole log)? It is
the more general answer, and it is more machinery than this milestone needs: it
requires a deterministic fold, replay on every write, and a compaction story.
The comparison above is one field and one branch, and it is correct for the
lifecycle actually modelled. If M2 shows it is insufficient, replay remains
available — the full event log is already persisted.

**Invoices are attributed by time, not by current state.** An invoice event
resolves to whichever halt episode's window contains its `occurred_at`, so an
invoice raised during a halt but delivered after reactivation still lands on
the right episode. That lineage is precisely what M2's backlog reconstruction
reads.

### 6.3 State transitions

| From | Event | Result |
|---|---|---|
| ACTIVE | `subscription.pending` | → PENDING |
| PENDING | `subscription.halted` | → HALTED, opens halt episode |
| PENDING | `subscription.activated` | → ACTIVE (recovered before halt; no episode) |
| HALTED | `subscription.activated` | → ACTIVE, closes halt episode |
| any | event asserting the current state | no-op, accepted |
| ACTIVE | `subscription.halted` | **rejected** `ILLEGAL_TRANSITION` |
| HALTED | `subscription.pending` | **rejected** `ILLEGAL_TRANSITION` |

`ACTIVE → HALTED` is refused deliberately. In the modelled lifecycle a halt
follows failed retries, so it must pass through PENDING; accepting a direct
halt would let a dropped `subscription.pending` event silently produce a halt
episode with no recorded cause. `HALTED → PENDING` is refused because leaving a
halt is a reactivation — a quiet slide back to PENDING would close an episode
with no reactivation to attribute it to.

Re-asserting the current state is a no-op rather than an error: at-least-once
delivery makes it routine, and failing it would turn normal webhook behaviour
into alert noise.

The table lives in `app/domain/state_machine.py` as a pure function — no I/O,
no clock, no database — so it is checkable by eye and testable without Mongo.

Writes use **compare-and-swap**: the update filter pins the status we believe
the subscription is in, so a concurrent writer that already moved it causes the
update to match nothing, reported as `CONCURRENT_MODIFICATION` rather than
overwriting someone else's transition.

### 6.4 Halt episodes

```jsonc
"halt_episodes": [
  { "episode_id": "he_1", "halted_at": "...", "reactivated_at": "...", "invoice_ids": ["inv_feb", "inv_mar"] }
]
```

Opened on entry to HALTED, closed on reactivation, never overwritten. At most
one episode is open at a time — guaranteed by the state machine, since the only
edge that opens one is `PENDING → HALTED` and CAS admits exactly one winner.

`ACTIVE → HALTED → ACTIVE → HALTED → ACTIVE` therefore produces two closed
episodes with distinct invoice sets. Under the scalar `halted_at` /
`reactivated_at` design the second halt would have overwritten the first and
its invoices would have lost their attribution.

### 6.5 Invoice lineage

`halt_episode_id` is authoritative; `generated_during_halt` is a derived
convenience field kept in sync with it and never read as the source of truth.

Two unique indexes protect the ledger: `invoice_id` catches replays, and the
compound `(subscription_id, billing_cycle)` makes double-billing a period
structurally impossible. The two are reported separately —
`DUPLICATE_INVOICE` versus `DUPLICATE_BILLING_CYCLE` — because one is a
harmless retry and the other means the platform believes it is billing the same
month twice.

### 6.6 Audit sequencing

Ordering comes from a per-subscription `seq`, not from `ts`. A single ingestion
writes four to six entries inside the same millisecond, and BSON datetimes
cannot separate them.

`seq` is allocated with an atomic single-document `$inc` on the subscription,
so concurrent writers cannot receive the same number. The unique index on
`(subscription_id, seq)` is the backstop. The audit repository exposes only
`append` and `list` — there is deliberately no update or delete.

### 6.7 Payment events in M1

`payment.failed` and `payment.succeeded` are recorded as ledger facts and do
**not** move subscription status; only the platform's own lifecycle events do
that, and inferring a halt from a failed payment would duplicate that
authority. `payment.succeeded` carrying an `invoice_id` settles that invoice.

### 6.8 What M1 deliberately does not do

No backlog aggregation, no recovery cases, no policy evaluation, no simulator,
no model, no LLM, no agent loop. M1 is the ledger those things will read.
