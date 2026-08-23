#!/usr/bin/env bash
# Canonical demo helper. Requires a running backend (make backend).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
API="${RECLAIM_API_URL:-http://127.0.0.1:8000}"
KEY="${INTERNAL_API_KEY:-}"
HDR=(-H "accept: application/json")
if [[ -n "$KEY" ]]; then
  HDR+=(-H "x-internal-api-key: $KEY")
fi

echo "Checking ${API}/healthz"
curl -fsS "${HDR[@]}" "${API}/healthz" >/dev/null

echo "Checking ${API}/readyz"
ready="$(curl -fsS -o /tmp/reclaim-ready.json -w "%{http_code}" "${HDR[@]}" "${API}/readyz" || true)"
if [[ "$ready" != "200" ]]; then
  echo "Backend is not ready:" >&2
  cat /tmp/reclaim-ready.json >&2
  exit 1
fi

ARTIFACT="${ROOT}/backend/app/ml/artifacts/recovery_model.joblib"
if [[ ! -f "$ARTIFACT" ]]; then
  echo "Missing committed model artifact at ${ARTIFACT}" >&2
  exit 1
fi

if [[ "${1:-}" == "reset" ]]; then
  echo "Generating canonical world (100 / seed 42 / budget 25)"
  body="$(curl -fsS "${HDR[@]}" -H "content-type: application/json" \
    -d '{"subscriber_count":100,"seed":42,"intervention_budget":25}' \
    "${API}/api/simulator/generate")"
  run_id="$(python3 -c 'import json,sys; print(json.load(sys.stdin)["run_id"])' <<<"$body")"
  echo "Running naive / rule_based / reclaim on ${run_id}"
  curl -fsS "${HDR[@]}" -H "content-type: application/json" \
    -d "{\"run_id\":\"${run_id}\",\"strategies\":[\"naive\",\"rule_based\",\"reclaim\"]}" \
    "${API}/api/simulator/run" >/dev/null
else
  run_id="$(curl -fsS "${HDR[@]}" "${API}/api/runs" \
    | python3 -c 'import json,sys; rows=json.load(sys.stdin); print(rows[0]["run_id"] if rows else "")')"
  if [[ -z "$run_id" ]]; then
    echo "No run exists. Re-run: make demo-reset" >&2
    exit 1
  fi
fi

echo
echo "run_id=${run_id}"
echo "Overview:     http://localhost:3000/?run=${run_id}"
echo "Cases:        http://localhost:3000/cases?run=${run_id}"
echo "Simulate:     http://localhost:3000/simulate?run=${run_id}"
echo "Model:        http://localhost:3000/model?run=${run_id}"
echo "Policy:       http://localhost:3000/policy?run=${run_id}"
echo
echo "SYNTHETIC SIMULATION — NOT PRODUCTION DATA"
