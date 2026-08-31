# RECLAIM

**Recover the revenue that comes back with the customer.**

A post-halt subscription recovery agent: it reconstructs stranded invoices,
estimates whether intervening is worth it, and executes **simulated** recovery
under a deterministic policy. Built for Razorpay Buildathon Track 03.

> **SYNTHETIC SIMULATION — NOT PRODUCTION DATA.**
> Every rupee figure is produced by a seeded synthetic laboratory.
> No Razorpay production data is used. No real payment is attempted.
> Claude is optional and off the measured economic path.

**What problem?** After `ACTIVE → PENDING → HALTED`, billing cycles keep
issuing invoices. When the subscriber later returns to `ACTIVE`, that
historical backlog is still unpaid.

**Why unusual?** Most “recovery” scores who will pay. RECLAIM scores what
**changes because we intervene**, under a shared intervention budget, then
re-checks policy immediately before acting.

**What was built?** Ledger → backlog → uplift model → policy → bounded
agent → simulated executor → audit. A judge-facing console on top.

**What proof exists?** 100-subscriber seed-42 worlds, three strategies on
the same `run_id`, TOCTOU / idempotency / atomic-budget tests, and a
real incident log — not reconstructed stories.

---

## The problem

When a subscription goes `ACTIVE → PENDING → HALTED`, the platform can
keep generating invoices that nobody pays. If the customer later returns
to `ACTIVE`, those invoices are still open — but they are not
automatically collectible. Service may have been suspended for those
periods.

That `HALTED → ACTIVE` edge is the recovery window. RECLAIM reconstructs
historical unpaid invoices, validates which ones are collectible
receivables, then asks whether a specific action is worth taking on
**eligible debt**, given policy, and whether they would have paid anyway.

## Why this matters

A merchant can lose the historical cycles that accumulated during a halt
even after the customer is back. Recovering them requires:

- a correct ledger (no double-claim, no overwritten halt)
- a policy that will not charge a domestic card or a disputed customer
- an economic ranking that does not treat “would have paid anyway” as a win
- an executor that re-validates the world immediately before acting

We do not invent industry recovery-rate statistics. This repo is a
laboratory, not a production collection system.

## What RECLAIM does

```
Detect halt → reactivation
  → reconstruct unpaid halt invoices (integer paise)
  → collectibility / service-entitlement gate
  → estimate P(recovery | action) and P(recovery | no_action)
      only over collectible eligible receivables
  → policy filter
  → rank by incremental expected value under a shared budget
  → validate again
  → simulated execution (M3 oracle)
  → audit + metrics
```

Claude may explain, answer constrained questions, or propose structured
extraction. It does not decide money movement.

## Architecture

```
Razorpay-like events
        ↓
Ledger / state machine / halt episodes
        ↓
Post-halt unpaid reconstruction (lineage, not date guesses)
        ↓
Collectibility gate (UNKNOWN fails closed)
        ↓
Feature builder  (no oracle, no latent, no strategy name)
        ↓
Recovery model   P(recovery | action)
        ↓
Uplift / incremental EV
        ↓
Policy filter    (authoritative)
        ↓
Bounded agent    observe → analyze → propose → validate → stop
        ↓
Simulated execution   (existing M3 oracle only)
        ↓
Audit + metrics
```

Claude is a **side-car**: explanation / Q&A / extraction only.

See [`docs/architecture.md`](docs/architecture.md) and
[`docs/agent.md`](docs/agent.md).

## Intelligence architecture

| Layer | Owns | Does not own |
|---|---|---|
| **ML** | Per-action probabilities, uplift, incremental EV, ranking | Policy, execution, metrics |
| **Policy** | What is permitted, escalated, or stopped | Probabilities |
| **LLM** | Grounded language over supplied facts | Any financial decision |
| **Agent** | Deterministic orchestration + validator | LLM-chosen actions |

`LLM_ENABLED` defaults to `false`. The Naive / Rule-based / RECLAIM
comparison is identical with Claude off.

## Recovery economics

```
uplift(A) = P(recovery | A) − P(recovery | no_action)

incremental_ev(A) = round(backlog_paise × uplift(A) − cost(A))
```

`NO_ACTION` EV is 0. Negative or zero EV means do nothing. UI copy says
“estimated intervention lift” and “expected incremental recovery,” never
“AI confidence.”

## Safety

- **Idempotency** — unique `event_id` and `recovery_actions.idempotency_key`
- **Policy revalidation** — planning decision and execution decision are both audited
- **TOCTOU** — plan payment link, customer opts out, execute is blocked
- **Budget atomicity** — Mongo `find_one_and_update` on remaining slots
- **Stopping rules** — success, dispute, opt-out, max attempts (3), cooldown, budget, EV ≤ 0
- **Audit** — append-only per-subscription sequence

## Synthetic evaluation

One seeded world, one policy, one oracle, one intervention budget. Only
the decision rule changes. Hidden `latent_payment_intent` is never a
strategy input. Persistence IDs (`run_id`, `case_id`) isolate Mongo;
oracle seeds use `synthetic_case_key`.

Details: [`docs/evaluation.md`](docs/evaluation.md).

## Baselines

| Strategy | Rule |
|---|---|
| **Naive** | Encounter order. First allowed automated action until the budget is gone. |
| **Rule-based** | Heuristic score (backlog + recency + historical success). Same actions and budget. |
| **RECLAIM** | Model incremental EV, then the same policy and budget. |

Canonical comparison **after the collectibility gate** (`subscriber_count=100`,
`seed=42`, `intervention_budget=25`):

Funnel: historical unpaid ₹16,71,822 → collectible ₹8,42,415 · review
₹5,67,448 · excluded ₹2,61,959. 23 collectible recovery cases (3 review-only
cases are outside the strategy universe).

| Strategy | Recovered | Incremental | Yield | Used |
|---|---:|---:|---:|---:|
| Naive | ₹5,53,459 | ₹2,95,483 | 65.70% | 16 |
| Rule-based | ₹5,53,459 | ₹2,95,483 | 65.70% | 16 |
| RECLAIM | ₹5,53,459 | ₹2,95,483 | 65.70% | 16 |

Yield denominator is collectible eligible receivable, not raw historical
invoices. All three strategies saw the same 23 cases and the same
₹8,42,415. On this seed they recovered the same amount. That is reported
as-is; the simulator was not retuned.

**Not comparable to M5/M6 rupee totals.** Those treated unpaid halt invoices
as eligible receivables (32 cases, ₹7,41,880 at risk). The eligible universe
changed.

These are **synthetic** figures, not Razorpay production statistics. If a
later seed loses, that result is reported.

## Running locally

```bash
git clone https://github.com/fahad2707/reclaim.git && cd reclaim
make setup
# put MONGODB_URI in .env
make backend      # http://127.0.0.1:8000
make frontend     # http://localhost:3000
```

Then `make demo-reset` (backend must already be up) to generate the
canonical world and print console URLs. Or walk
[`docs/demo-script.md`](docs/demo-script.md).

The Evaluation page (`/evaluation`) runs an in-memory collectibility
benchmark. It does not write Mongo. CLI: `make benchmark`.


## Tests

```bash
make check              # ruff + tsc + pytest
make test               # backend unit + integration (one process)
make test-unit
make test-integration   # throwaway reclaim_test_* database
cd frontend && npm run lint && npm run typecheck && npm test && npm run build
```

## Deployment

| Piece | Host | Notes |
|---|---|---|
| Frontend | Vercel | Project root `frontend/`. Server-only `RECLAIM_API_URL`, `INTERNAL_API_KEY`. |
| Backend | Railway | `Dockerfile`, `/healthz`, `/readyz`. |
| Database | MongoDB Atlas | Use `reclaim_demo`. Never a test DB. |

See [`docs/deployment.md`](docs/deployment.md). Deploy with
`LLM_ENABLED=false` until the deterministic path is green.

## Environment variables

Templates: [`.env.example`](.env.example),
[`frontend/.env.local.example`](frontend/.env.local.example).
No real secrets are committed.

`RECLAIM_API_URL` and `INTERNAL_API_KEY` must **not** be `NEXT_PUBLIC_`.

## Repository layout

```
backend/app/          API, ledger, policy, ML, agent, LLM side-car
backend/tests/        unit + integration + adversarial
frontend/             Next.js console (proxy at /api/[...proxy])
docs/                 architecture, policy, evaluation, agent, incidents
scripts/demo.sh       canonical generate / run / URLs
```

## Known limitations

- Synthetic data and a synthetic outcome oracle only
- No production Razorpay connection
- No real charge, payment-link, WhatsApp, SMS, or voice APIs
- No partial invoice settlement (full backlog or nothing)
- LLM optional; explanations fall back to deterministic copy
- Model trained on the same synthetic family as the demo
- Policy action space is four actions
- `POST /api/model/train` writes an ephemeral file on Railway

## What broke during development

Real failures only: [`docs/incidents.md`](docs/incidents.md).

Strongest “what actually broke” candidates: INC-007 (historical events
rejected as stale), INC-010 (same-seed oracle hashed `case_id`),
INC-011 (opt-out TOCTOU hid behind a model re-score).

## Disclaimer

This is a synthetic recovery laboratory. It is not a Razorpay production
system. Simulated payments do not move money.
