# RECLAIM — Revenue Recovery OS

**Recover the revenue that comes back with the customer.**

Post-halt subscription revenue recovery agent. Razorpay Buildathon — Track 03.

> **SYNTHETIC SIMULATION — NOT PRODUCTION DATA.**
> Every number this system produces comes from a seeded synthetic environment.
> No Razorpay production data is used, and no real money moves.

---

## Status

**M0 — Foundation.** Backend, frontend, and the connection between them.
No recovery logic, simulator, model, policy engine, or LLM integration yet.

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
make check       # ruff + tsc + pytest
make test        # pytest only
```

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
