# RECLAIM — Deployment

> **SYNTHETIC SIMULATION — NOT PRODUCTION DATA.**
> Deployed environments still run the synthetic laboratory. No real Razorpay
> money movement.

## Topology

```
browser
  → Vercel (Next.js)
      → same-origin /api/* proxy
          → Railway (FastAPI)
              → MongoDB Atlas
```

The browser never holds `INTERNAL_API_KEY` or `RECLAIM_API_URL`. Those are
server-only on Vercel (`RECLAIM_API_URL`, `INTERNAL_API_KEY` — not
`NEXT_PUBLIC_*`).

CORS is not the primary path. Still set `CORS_ORIGINS` to the Vercel URL.

## Railway (backend)

- Runtime: Python 3.12 via the repo `Dockerfile`
- Start: `uv run uvicorn app.main:app --host 0.0.0.0 --port $PORT`
  (Railway injects `PORT`; override the Dockerfile `CMD` if needed)
- Health: `GET /healthz`  Readiness: `GET /readyz`
- Production logging is JSON (`APP_ENV=production`)

Required variables (no secrets in git):

| Name | Notes |
|---|---|
| `MONGODB_URI` | Atlas SRV string |
| `MONGODB_DB` | Use `reclaim_demo`, never a test DB |
| `INTERNAL_API_KEY` | Shared with Vercel |
| `APP_ENV` | `production` |
| `CORS_ORIGINS` | Vercel origin |
| `LLM_ENABLED` | `false` until Claude is configured |
| `ANTHROPIC_API_KEY` | empty unless enabling the side-car |
| `MODEL_ARTIFACT_PATH` | default committed `app/ml/artifacts/recovery_model.joblib` |

Railway's filesystem is ephemeral. The committed joblib is the demo model.
`POST /api/model/train` writes a local file that **will be lost on restart**.
Do not treat production training as durable storage.

## Vercel (frontend)

Set the project root to `frontend/`.

| Name | Notes |
|---|---|
| `RECLAIM_API_URL` | Railway public origin, no trailing path |
| `INTERNAL_API_KEY` | Same value as Railway |
| `NEXT_PUBLIC_APP_ENV` | `production` (display only) |

## MongoDB Atlas

Create or name a database `reclaim_demo`. Indexes are created on API
startup (`ensure_indexes`). Integration tests use `reclaim_test_*` and
drop those databases; they never target `reclaim` or `reclaim_demo`.

## First-boot smoke

```
GET  {railway}/healthz
GET  {railway}/readyz
open {vercel}/
open {vercel}/simulate
generate seed 42 / 100 subscribers / budget 25
run naive + rule_based + reclaim
open Overview, Cases, Case detail, Model, Policy
Plan (no execution) → Run simulated recovery
```

Leave `LLM_ENABLED=false` until this path is green. Claude is optional.
