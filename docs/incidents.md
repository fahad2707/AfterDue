# Incident log

Real failures encountered while building RECLAIM, recorded when they happened.
Nothing here is reconstructed or invented for the submission.

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
