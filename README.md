# RECLAIM — Revenue Recovery OS

**Recover the revenue that comes back with the customer.**

Post-halt subscription revenue recovery agent. Razorpay Buildathon — Track 03.

> **SYNTHETIC SIMULATION — NOT PRODUCTION DATA.**
> Every number this system produces comes from a seeded synthetic environment.
> No Razorpay production data is used, and no real money moves.

---

## Status

**M0 — Foundation.** Backend, frontend, and the connection between them. Done.

**M1 — Ledger and events.** Collections and indexes, idempotent event
ingestion, the subscription state machine, halt episodes, invoice lineage, and
an append-only audit trail. Done.

**M2 — Backlog and policy.** Reconstructs the unpaid historical backlog for a
closed halt episode, opens exactly one recovery case, and evaluates a
deterministic policy engine. No action is executed.

**M3 — Synthetic world and baselines.** Seeded generator, counterfactual
oracle, naive and rule-based strategies, intervention budget, isolated
`run_id`s. Done. No ML and no LLM.

**M4 — Vertical demo spine.** Console for simulation, revenue at risk,
baseline comparison, recovery queue, case detail, policy, and audit.
Observational only. Done.

Still absent by design: uplift model, Claude, agent loop, and
payment execution.

---

## What this is

When a subscription goes `ACTIVE → PENDING → HALTED`, billing cycles keep
generating invoices that nobody pays. If the customer later fixes their payment
method and the subscription returns to `ACTIVE`, that backlog is still stranded.

RECLAIM detects the `HALTED → ACTIVE` transition, reconstructs the unpaid
invoice backlog for that halt episode, estimates how much of it is recoverable
*because of an intervention rather than anyway*, checks a deterministic policy
engine for what is permitted, executes a bounded simulated action, and measures
the rupees recovered against two baseline strategies on the identical synthetic
world.

The AI never executes anything. Policy is authoritative.

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

Open http://localhost:3000 — it renders live status for every M0 dependency.

## Checks

```bash
make check              # ruff + tsc + pytest
make test               # both suites in one process
make test-unit          # no database needed
make test-integration   # needs MONGODB_URI; uses a throwaway database
```

Integration tests create `reclaim_test_<random>` and drop it afterwards. They
never touch the `reclaim` database.

## API (M1)

| Method | Path | Purpose |
|---|---|---|
| POST | `/api/customers` | Create a customer |
| POST | `/api/subscriptions` | Create a subscription |
| POST | `/api/events` | Ingest one platform event (idempotent) |
| GET | `/api/subscriptions/{id}` | Current state and halt episodes |
| GET | `/api/subscriptions/{id}/events` | Event history |
| GET | `/api/subscriptions/{id}/audit` | Append-only audit trail |
| GET | `/api/invoices?subscription_id=` | Invoices with halt-episode lineage |
| GET | `/api/recovery-cases?run_id=` | Cases for a run, largest backlog first |
| GET | `/api/recovery-cases/{id}` | Case, unpaid invoices, live policy decision |
| GET | `/api/recovery-cases/{id}/audit` | Subscription audit filtered to the episode |
| POST | `/api/recovery-cases/reconcile` | Create missing cases for closed episodes |
| GET | `/api/policy/config` | Version, rules, reason codes, provenance |
| POST | `/api/policy/evaluate` | Dry-run policy decision; writes nothing |
| POST | `/api/simulator/generate` | Seeded synthetic world (`synthetic: true`) |
| POST | `/api/simulator/run` | Naive / rule-based comparison on one run |
| GET | `/api/runs` | Recent simulation runs |
| GET | `/api/runs/{run_id}` | Config, world summary, strategy metrics |
| GET | `/api/dashboard/summary?run_id=` | Composed overview metrics for one run |

Redelivering an `event_id` answers `200` with `outcome: "duplicate"` and
changes nothing. See [`docs/architecture.md §6`](docs/architecture.md) for the
transition table and [`docs/policy.md`](docs/policy.md) for v1 rules.

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
