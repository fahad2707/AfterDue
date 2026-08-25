# Incident log

Real failures encountered while building RECLAIM, recorded when they happened.
Nothing here is reconstructed or invented for the submission.

**Strongest “what broke” candidates for a later pitch (do not dramatize):**

1. **INC-007** — best 2AM candidate. A fixture stamped `last_state_change_at`
   on create, so every historical replay looked stale. That would have
   broken M2’s simulator, not just one test.
2. **INC-012** — invoice existence was treated as collectibility. The code
   worked; the assumption didn’t.
3. **INC-010** — same-seed worlds diverged because the oracle hashed
   `case_id` (which embeds `run_id`).
4. **INC-011** — opt-out TOCTOU returned `POLICY_BLOCKED` because execute
   re-scored the model after the flag change.

---

## INC-001 — Auth middleware returned 500 instead of 401

**Milestone:** M0
**Severity:** would have been a production bug, caught by test

**Problem.** The shared-secret check on `/api/*` raised
`HTTPException(401)` from an `@app.middleware("http")` function. The test
asserting a 401 for a missing key failed with an uncaught
`fastapi.exceptions.HTTPException` propagating all the way out of the ASGI
stack.

**Cause.** HTTP middleware registered with `@app.middleware("http")` wraps
`ExceptionMiddleware`, so it sits *outside* the layer that converts
`HTTPException` into a response. A raised `HTTPException` there is just an
unhandled exception: the client gets a 500, and with debug enabled it would get
a traceback.

**Investigation.** The pytest traceback showed the exception escaping through
`starlette/middleware/errors.py` rather than being handled — which located the
problem at the middleware layer rather than in the check itself.

**Fix.** Return a `JSONResponse(status_code=401, ...)` directly instead of
raising.

**Prevention.** The three middleware tests (`missing key → 401`,
`valid key → 200`, `health endpoints exempt`) run on every `make test`. The
reason is recorded in a docstring on the middleware so it does not regress
during a refactor.

---

## INC-002 — Frontend env template was silently untracked

**Milestone:** M0
**Severity:** would have broken a fresh clone

**Problem.** `frontend/.env.local.example` — the file that documents how to
configure the frontend — was being excluded from git.

**Cause.** `create-next-app` generates a `frontend/.gitignore` containing
`.env*`. The root `.gitignore` had a `!frontend/.env.local.example` negation,
but a `.gitignore` in a subdirectory takes precedence over the root for paths
inside it, so the negation never applied.

**Investigation.** `git check-ignore -v` was misleading: it exits 0 and prints
the matching pattern even when that pattern is a *negation*, so it appeared to
report "ignored" both before and after the fix. `git add --dry-run` was the
reliable check — it lists what would actually be staged.

**Fix.** Added `!.env.local.example` to `frontend/.gitignore` itself.

**Prevention.** Verified with `git add --dry-run` on both files: the templates
are listed, and `.env` / `.env.local` are explicitly refused as ignored.

---

## INC-005 — Test suite hung forever after the two suites ran together

**Milestone:** M1
**Severity:** real defect in connection lifecycle, surfaced by tests

**Problem.** Unit tests passed. Integration tests passed. Running
`pytest` over both in one process hung indefinitely with no output — not a
failure, no traceback, just a process that never returned.

**Cause.** `MongoConnection` is a process-wide singleton. The integration suite
connects it to a test database; the unit suite then rebuilds the app with an
empty `MONGODB_URI`, and `connect()` took an early return without clearing the
existing client. So the unit suite inherited a live `AsyncMongoClient` bound to
the integration suite's event loop, which had already been torn down. The first
`/readyz` ping issued a command on a handle whose loop no longer existed and
blocked forever. `pytest -q` piped through `tail` buffers output, so the hang
produced total silence rather than a partial run.

**Investigation.** Suspicion fell on the shared singleton because it is the only
state that survives `importlib.reload(app.main)`. Reading `connect()` showed the
early return leaving `self._client` untouched.

**Fix.** `connect()` now always clears any existing client before deciding what
to do. It drops the reference rather than awaiting `close()` on it — awaiting a
client bound to a dead loop is the very hang being avoided.

**Prevention.** This is a real production behaviour, not only a test artifact:
any code path that reconnects (a config reload, a retry after an outage) would
have inherited the same stale handle. The full suite now runs both directories
in one process on every `make test`, so a regression reproduces immediately.

**Worth knowing generally:** async database clients are bound to the event loop
that created them. A singleton that outlives its loop is a deadlock waiting for
a second caller.

---

## INC-006 — A test that measured network latency instead of the invariant

**Milestone:** M1
**Severity:** flaky test, caught on first run

**Problem.** `test_audit_ordering_survives_identical_timestamps` failed with
"expected a timestamp collision".

**Cause.** The test wrote several audit entries over HTTP and asserted that at
least two shared a millisecond timestamp, in order to then prove that `seq`
still ordered them. Against Atlas, each write takes several milliseconds, so no
collision occurred. The assertion was really measuring round-trip time.

**Fix.** Freeze the clock with `monkeypatch` so every entry genuinely lands on
the same millisecond, then assert unique ascending `seq`. The invariant is now
tested directly instead of being inferred from timing.

**Prevention.** Worth stating as a rule for this codebase: a test that depends
on how long an I/O call takes is not testing the property it claims to test. It
will pass on a fast machine, fail in CI, and teach the team to re-run it.

---

## INC-004 — Readiness reported healthy against dead credentials

**Milestone:** M0
**Severity:** observability gap, no data impact

**Problem.** The Atlas database password was rotated. `/readyz` continued to
answer `200 {"ready": true, "mongodb": {"ok": true}}` even though the
credentials in `.env` were no longer valid.

**Cause.** The readiness check issues `admin.command("ping")` through the
existing `AsyncMongoClient`. The driver reuses an already-authenticated
connection from its pool, and authentication happens at connection
establishment rather than per command. So the probe measured the health of
connections opened *before* the rotation, not the validity of the credentials
the process currently holds.

**Investigation.** Opening a brand-new `AsyncMongoClient` with the same URI
failed immediately with `OperationFailure: bad auth : authentication failed
(AtlasError 8000)`, which isolated the difference to connection reuse rather
than to Atlas or the URI.

**Fix.** Restarting the process surfaced the failure correctly — `/readyz`
then reported the auth error, which is the behaviour a deploy or a container
restart would produce anyway.

**Why we are not "fixing" this further.** Forcing a fresh authenticated
connection on every readiness probe would add latency and connection churn to
an endpoint that platforms poll frequently, to detect a condition that any
restart already reveals. The honest characterisation, now recorded here and in
the endpoint's docstring, is that `/readyz` reports **the health of the current
connection pool**, not the current validity of credentials.

**Worth knowing generally:** a green health check can describe a stale
connection rather than a working dependency. This is the same class of problem
as a load balancer keeping a dying instance in rotation.

---

## INC-003 — Sandbox and toolchain friction

**Milestone:** M0
**Severity:** minor, worth noting for reproducibility

**Problem.** The machine had only Python 3.14 installed, and `pip install uv`
failed with `EPERM` writing to `~/Library/Python`. `create-next-app` failed the
same way on `~/Library/Preferences`.

**Cause.** Both tools write outside the project directory for user-level
installs and preference storage.

**Fix.** Installed `uv` via the official installer to `~/.local/bin`, then
pinned the backend to Python 3.12 with `backend/.python-version` and
`requires-python = ">=3.12,<3.13"`.

**Prevention.** Python 3.14 is never used by this project. `uv` resolves 3.12
from the pin, so contributors and Railway get the same interpreter regardless
of what the host has installed.

---

## INC-007 — Every historical event was rejected as stale, and the tests said fine

**Milestone:** M1
**Severity:** real defect; would have blocked M2 entirely

**Problem.** The full M1 test suite passed — 62 tests, including four
specifically about out-of-order events. A manual `curl` walk through the same
lifecycle then rejected every single lifecycle event with `STALE_EVENT`.

**Cause.** `POST /api/subscriptions` seeded `last_state_change_at` from
`created_at`, which defaults to now. Replaying a timeline dated February into a
subscription created today meant every event's `occurred_at` was older than
`last_state_change_at`, so the staleness guard refused all of them.

**Why the tests missed it.** The integration helper always passed an explicit
`created_at` of `2026-01-01` and then sent events at `T0 + hours`. Every test
timeline ran *forward from the seeded creation time*, so the fixture quietly
guaranteed the condition the guard needed. The tests were self-consistent and
wrong together.

**Fix.** `last_state_change_at` is now nullable and starts as `None`. Creating
a subscription *sets* its state, it does not *change* it, so there is no prior
transition for an incoming event to contradict. The staleness comparison is
skipped until the first real transition, after which it applies exactly as
before.

**Prevention.** Added a regression test that creates a subscription with no
explicit `created_at` and replays a 2020 timeline into it, then confirms the
guard still fires for a genuinely older event afterwards.

**Worth knowing generally:** this is the failure mode where a shared test
fixture encodes the same wrong assumption as the code. The suite cannot catch
it, because the fixture and the defect agree. Manual exercise of the real API
found it in one command — which is an argument for doing that at every
milestone rather than trusting a green suite. M2's simulator replays historical
timelines by definition, so this would have surfaced later as a total failure
with a much less obvious cause.

---

## INC-008 — Simulator package init circular-imported SimulationRun

**Milestone:** M3
**Severity:** real defect; every integration test that built the app failed at import

**Problem.** `pytest tests/integration/test_simulator.py` errored seven times
in setup with `ImportError: cannot import name 'SimulationRun' from partially
initialized module 'app.models.simulation'`.

**Cause.** `app.models.simulation` imported `SimulationConfig` from
`app.simulator.config`. Importing the `app.simulator` package ran
`simulator/__init__.py`, which imported `SimulationRunner`, which imported
`SimulationRun` before that class finished defining.

**Fix.** The package init now exports only `SimulationConfig`. Callers that
need the runner or oracle import those modules directly.

**Prevention.** The integration suite imports the app; a cycle cannot hide
behind unit tests that import leaf modules.

---

## INC-009 — Leak test failed because a docstring mentioned the oracle

**Milestone:** M3
**Severity:** test defect, not a strategy leak

**Problem.** `test_strategy_module_cannot_see_oracle_or_latent` failed because
`strategies.py` contains the sentence "They do not import the oracle."

**Cause.** The test banned the substring `oracle` anywhere in the file. A
comment that *denied* the leak looked like the leak.

**Fix.** The test now checks the import graph (`from app.simulator.oracle`,
`OutcomeOracle`, `latent_payment_intent` on `CaseView`) rather than a word
search.

---

## INC-010 — Same-seed worlds diverged because the oracle hashed `case_id`

**Milestone:** M3
**Severity:** reproducibility defect; caught by external review, not by the suite

**Problem.** Two `generate` calls with the same `SimulationConfig` and seed
materialised equivalent subscribers, but oracle outcomes (and therefore
strategy metrics) differed.

**Cause.** The oracle seeded `Random` from `(run_seed, case_id, action)` and
latent intent from `(run_seed, customer_id)`. Both persistence IDs embed
`run_id`, which is unique per generate. The suite only asserted matching
world-summary *counts* and same-run strategy replay, so the gap was
invisible.

**Fix.** Seed-stable `synthetic_customer_key` / `synthetic_case_key` (e.g.
`subscriber_0042_halt_01`) are written onto synthetic customers and cases.
The oracle now hashes `(run_seed, synthetic_case_key, action)`. Latent
intent uses `(run_seed, synthetic_customer_key)`. `run_id` / `case_id`
remain the Mongo isolation keys.

**Prevention.** Integration test generates two seed-42 worlds, asserts
isolated persistence IDs, identical features, identical latents, identical
per-action counterfactuals, and identical strategy metrics.

---

## INC-011 — Opt-out TOCTOU reported POLICY_BLOCKED because the model re-scored

**Milestone:** M6
**Severity:** would have hidden the validator demo; caught by the required TOCTOU test

**Problem.** Plan recommended a payment link. After the customer was mutated
to opted-out, execute returned `POLICY_BLOCKED` instead of
`CUSTOMER_OPTED_OUT`.

**Cause.** Execute rebuilt `CaseView` from the latest customer. Opt-out is a
model feature, so the ranking could change before the validator ran. The
generic “action not allowed” branch then fired, or a different action was
proposed.

**Fix.** Proposal scoring uses a copy of the customer with dispute/opt-out
cleared. The validator applies the real flags and maps
`CUSTOMER_OPTED_OUT` / `ACTIVE_DISPUTE` reason codes before the generic
`POLICY_BLOCKED` stop.

**Prevention.** `test_toctou_opt_out_blocks_execution` plans a payment link,
mutates opt-out in Mongo, executes, and asserts `CUSTOMER_OPTED_OUT`, no
oracle row, and no budget claim.

---

## INC-012 — Invoice existence was treated as collectibility

**Milestone:** collectibility gate
**Severity:** material business-model flaw; caught in design review before
treating a suspend-on-halt merchant as recoverable revenue

**Symptom.** A merchant that suspends service during halt could still
generate halt-period invoices. RECLAIM treated those unpaid invoices as
recoverable revenue after reactivation.

**Root cause.** The backlog builder established invoice lineage and unpaid
status. The architecture had no service-entitlement / collectibility
boundary. Invoice existence was incorrectly treated as proof of
collectibility.

**Impact.** The agent could economically optimize recovery of invoices for
periods in which service was not actually delivered.

**Fix.** Inserted a deterministic collectibility validation step between
historical unpaid reconstruction and recovery-case economic eligibility.
UNKNOWN service delivery fails closed to `REVIEW_REQUIRED`.
`backlog_amount_paise` is now collectible eligible receivable only.

The code worked. The assumption didn't.

**Prevention.** Suspended / delivered / mixed entitlement tests, including a
mandatory May/June/July mixed case (₹5,000 collectible / excluded / review).
Reconciliation uses the same `RecoveryWindowService` path. All three
strategies share the post-gate universe.

