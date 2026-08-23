# RECLAIM — Revenue Recovery OS

**Recover the revenue that comes back with the customer.**

Post-halt subscription revenue recovery agent. Razorpay Buildathon — Track 03.

> **SYNTHETIC SIMULATION — NOT PRODUCTION DATA.**
> Every number this system produces comes from a seeded synthetic environment.
> No Razorpay production data is used, and no real money moves.
> There is no Claude / LLM layer. All economic results are synthetic.

---

## Status

**M0 — Foundation.** FastAPI, Next.js, Atlas, health checks, and a
server-side API proxy. Done.

**M1 — Ledger and events.** Collections and indexes, idempotent event
ingestion, the subscription state machine, halt episodes, invoice lineage,
and an append-only audit trail. Done.

**M2 — Backlog and policy.** Reconstructs the unpaid historical backlog for a
closed halt episode, opens exactly one recovery case, and evaluates a
deterministic policy engine with provenance. No action is executed. Done.

**M3 — Synthetic laboratory.** Seeded world generator, hidden-latent
counterfactual oracle, intervention budget, and two baselines (Naive,
Rule-based) compared on an identical world. Done.

**M4 — Vertical demo spine.** A financial-ops console: simulation control,
revenue-at-risk overview, strategy comparison, recovery queue, case detail,
policy inspector, and audit timeline. Observational only. Done.

**M5 — Recovery model.** Shared feature builder, randomized synthetic
training, per-action probabilities, estimated intervention lift,
incremental expected value, and a `ReclaimStrategy` that ranks under the
same policy and intervention budget as the baselines. Done.

**Not built yet:** Claude / language layer (M6) and payment execution.

---

## What this is

When a subscription goes `ACTIVE → PENDING → HALTED`, billing cycles keep
generating invoices that nobody pays. If the customer later returns to
`ACTIVE`, that historical backlog is still stranded.

RECLAIM treats that `HALTED → ACTIVE` edge as the recovery window:

1. **Ledger.** Every platform event is claimed once. The state machine
   records halt episodes so a second halt cannot overwrite the first.
2. **Backlog.** Outstanding invoices for the closed episode are reconstructed
   by lineage (`halt_episode_id`), not by guessing date windows. Money is
   integer paise.
3. **Policy.** A typed v1 engine subtracts disallowed actions. Domestic-card
   manual charge is documented platform behavior; other rules are labelled
   assumption or safety guardrail. Policy is authoritative. No action is
   executed from the console.
4. **Synthetic laboratory.** A seeded generator materialises customers,
   halt episodes, and cases through the real ingest path. An outcome oracle
   answers counterfactuals for `no_action` / payment link / manual charge
   without knowing which strategy asked. Hidden `latent_payment_intent` is
   never a strategy input.
5. **Baselines.** Naive and Rule-based choose among policy-allowed actions
   under the same intervention budget, on the same `run_id`.
6. **RECLAIM strategy.** A recovery model scores permitted actions, estimates
   intervention lift versus doing nothing, and spends the same budget on the
   highest positive incremental EV. Blocked actions stay blocked. Negative EV
   is allowed to mean “do nothing.”
7. **Console.** `/` `/cases` `/cases/[id]` `/simulate` `/model` `/policy`
   let a reviewer inspect one isolated run: revenue at risk, three-strategy
   comparison, the queue (model ranking when analysis exists), case-level
   model estimates, policy provenance, and the audit trail.

All economic results are synthetic. They are not Razorpay production
statistics.

---

## Requirements

- **Python 3.12** (managed by [`uv`](https://docs.astral.sh/uv/) — do not use the system Python)
- **Node 20+** (developed on Node 24)
- **MongoDB Atlas** connection string

---

## Setup

```bash
git clone <repo> && cd Reclaim
make setup
```

Then put your Atlas connection string in `.env`:

```
MONGODB_URI=mongodb+srv://<user>:<password>@<cluster>/?retryWrites=true&w=majority
```

`make setup` copies `.env.example → .env` and
`frontend/.env.local.example → frontend/.env.local`. Neither real env file is
ever committed.

## Running

Two terminals:

```bash
make backend     # FastAPI on http://127.0.0.1:8000
make frontend    # Next.js on http://localhost:3000
```

Open http://localhost:3000 — pick or generate a simulation run, then walk
Overview → Cases → Case detail → Policy. See [`docs/demo-script.md`](docs/demo-script.md).

## Checks

```bash
make check              # ruff + tsc + pytest
make test               # both backend suites in one process
make test-unit          # no database needed
make test-integration   # needs MONGODB_URI; uses a throwaway database
```

Frontend: `cd frontend && npm run lint && npm run typecheck && npm test && npm run build`

Integration tests create `reclaim_test_<random>` and drop it afterwards. They
never touch the `reclaim` database.

## API

| Method | Path | Purpose |
|---|---|---|
| POST | `/api/customers` | Create a customer |
| POST | `/api/subscriptions` | Create a subscription |
| POST | `/api/events` | Ingest one platform event (idempotent) |
| GET | `/api/subscriptions/{id}` | Current state and halt episodes |
| GET | `/api/subscriptions/{id}/events` | Event history |
| GET | `/api/subscriptions/{id}/audit` | Append-only audit trail |
| GET | `/api/invoices?subscription_id=` | Invoices with halt-episode lineage |
| GET | `/api/recovery-cases?run_id=` | Cases for a run |
| GET | `/api/recovery-cases/{id}` | Case, unpaid invoices, live policy decision |
| GET | `/api/recovery-cases/{id}/audit` | Subscription audit filtered to the episode |
| POST | `/api/recovery-cases/reconcile` | Create missing cases for closed episodes |
| GET | `/api/policy/config` | Version, rules, reason codes, provenance |
| POST | `/api/policy/evaluate` | Dry-run policy decision; writes nothing |
| POST | `/api/simulator/generate` | Seeded synthetic world (`synthetic: true`) |
| POST | `/api/simulator/run` | Naive / Rule-based / RECLAIM on one run |
| POST | `/api/model/train` | Train and activate a recovery-model artifact |
| POST | `/api/model/evaluate` | Held-out evaluation of the active artifact |
| GET | `/api/model/active` | Active model metadata |
| GET | `/api/model/metrics` | Classification and Brier summary |
| GET | `/api/recovery-cases/{id}/analysis` | Per-case model estimates |
| GET | `/api/runs` | Recent simulation runs |
| GET | `/api/runs/{run_id}` | Config, world summary, strategy metrics |
| GET | `/api/dashboard/summary?run_id=` | Composed overview metrics for one run |

Redelivering an `event_id` answers `200` with `outcome: "duplicate"` and
changes nothing. See [`docs/architecture.md`](docs/architecture.md),
[`docs/policy.md`](docs/policy.md), and [`docs/evaluation.md`](docs/evaluation.md).

---

## Architecture notes

Documented in [`docs/architecture.md`](docs/architecture.md).
Real development failures are logged in [`docs/incidents.md`](docs/incidents.md)
as they happen — none of them are invented after the fact.

## Environment variables

See [`.env.example`](.env.example) and
[`frontend/.env.local.example`](frontend/.env.local.example). Both are committed
with empty values.

`RECLAIM_API_URL` and `INTERNAL_API_KEY` are intentionally **not** prefixed with
`NEXT_PUBLIC_`: the browser talks only to same-origin `/api/*`, which the
Next.js server proxies to FastAPI.
