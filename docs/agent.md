# RECLAIM — Bounded recovery agent (M6)

> **SYNTHETIC SIMULATION — NOT PRODUCTION DATA.**
> Execution is simulated. No Razorpay charge, payment-link, WhatsApp, SMS,
> or voice API is called.

The measured economic path is unchanged and does not consult a language
model:

```
Recovery Case
  → Policy
  → Model
  → Uplift
  → Incremental EV
  → Action Ranking
  → Validator
  → Simulated Executor
  → Audit
  → Metrics
```

Claude is a **side-car**. It may explain, extract, or answer questions. It
does not decide policy, probabilities, uplift, incremental EV, budget,
contact eligibility, or metrics.

The entire experiment must run with `LLM_ENABLED=false`.

---

## Deterministic orchestration

`RecoveryAgent` is ordinary Python. One HTTP execute call is one bounded
attempt:

1. **Observe** — reload case, customer, subscription.
2. **Analyze** — policy + recovery model (if an artifact exists).
3. **Propose** — `recommend_action(policy, analysis)`. The model may
   suggest an action only if it is in the proposal policy's allowed set.
   Dispute and opt-out are *not* applied at proposal time so a mid-flight
   flag change is visible as a blocked execution rather than a silent
   replan to `no_action`.
4. **Validate** — `ActionValidator` re-evaluates latest policy immediately
   before acting.
5. **Execute simulation** — `SimulatedExecutor` calls the existing M3
   `OutcomeOracle`. There is no second outcome engine.
6. **Observe outcome** — audit `OUTCOME_OBSERVED`.
7. **Stop / escalate** — machine-readable `stop_reason`. No sleep in the
   request. If contact cooldown is active, the run stores `next_eligible_at`
   and stops.

A hard iteration cap (`AGENT_HARD_ITERATION_CAP`, default 4) and
`MAX_RECOVERY_ATTEMPTS` (default 3) bound the loop even if state is wrong.

---

## LLM side-car

Callers depend on `LanguageProvider.generate_structured(...)`, not on
Anthropic. The only Anthropic import lives in `app/llm/anthropic_provider.py`
and is loaded only when `LLM_ENABLED=true` and a key is present.

Startup never requires a key. If the provider is missing, times out, rate
limits, or returns malformed JSON, `CaseExplanationService` uses
`DeterministicExplanationService` (the functions in `app/llm/deterministic.py`).

Structured schemas (`CaseExplanation`, `ExtractionProposal`, `QAAnswer`)
reject extra keys. Ungrounded explanations (invented reason codes,
“guaranteed recovery”, oracle / latent talk) are discarded.

Claude is not called on case-detail page load. The UI offers
“Generate AI explanation” as an explicit action.

---

## Validator and TOCTOU

Planning-time policy and execution-time policy are both recorded.

Immediately before simulation the validator reloads the decision inputs and
checks:

- case still open
- no active dispute
- no opt-out on a payment-link contact
- attempt bound
- action still permitted
- contact cooldown
- budget remaining
- action not already executed under the same idempotency key

Classic demo:

1. Plan — payment link permitted and recommended.
2. Customer is mutated to opted-out.
3. Execute — `POLICY_REVALIDATED` → payment link blocked → no oracle
   call → no budget claim.

---

## Idempotency

Each recovery action has `idempotency_key`, unique in MongoDB.

Default identity: `{run_id}:{case_id}:{action}:{attempt_number}`.

The execute API also accepts an explicit `idempotency_key`. A retry of the
same key returns the existing row: one budget claim, one oracle outcome,
one contact.

A crash after insert and before oracle completion can leave a
`validated` row. A later retry with the same key will not double-claim
budget; completing a stuck row is a follow-up concern, not a second charge.

---

## Budget atomicity

Intervention slots live in `intervention_budgets`. Claim is a single
`find_one_and_update`:

```
filter: { run_id, $expr: { $lt: ["$claimed", "$limit"] } }
update: { $inc: { claimed: 1 } }
```

Two workers cannot both take the last slot. Check-then-decrement is not used.

Payment link and manual charge consume a slot. Escalation does not.

---

## Stopping rules

| `stop_reason` | Meaning |
|---|---|
| `RECOVERY_SUCCEEDED` | Oracle paid; case closed; full backlog recorded. Partial invoice settlement is **not** modeled. |
| `ACTIVE_DISPUTE` | Escalation. No automated collection. |
| `CUSTOMER_OPTED_OUT` | Payment-link contact blocked. |
| `MAX_ATTEMPTS_REACHED` | `attempt_count >= 3`. No fourth attempt. |
| `HARD_ITERATION_CAP` | Absolute bound if state is corrupt. |
| `NEGATIVE_OR_ZERO_EV` | Model estimate exists and incremental EV ≤ 0. |
| `CASE_CLOSED` | Nothing further to do. |
| `BUDGET_EXHAUSTED` | Atomic claim lost or remaining was 0. |
| `CONTACT_COOLDOWN_ACTIVE` | `next_eligible_at` set; request does not sleep. |
| `POLICY_BLOCKED` / `NO_AUTOMATED_ACTION` | Validator or policy forbids the action. |
| `ALREADY_EXECUTED` | Idempotent replay. |
| `SYSTEM_FAILURE` | Reserved for infrastructure faults. Unknown system outcomes are not counted as recovery. |

---

## Execution states

**Agent run:** `planned` → `validated` → `executed` | `stopped` | `escalated` | `failed`.

**Recovery action:** `planned` → `validated` → `executed` | `blocked` | `failed`.

Business failure (oracle `unpaid`) may allow a later attempt. System
failure must not be recorded as paid.

---

## Unstructured extraction

`POST /api/recovery-cases/{id}/extract` turns customer text into a
**proposal**. It does not move money and does not change policy by itself.

Pipeline: text → structured extraction → schema + span validation →
optional accepted context update (`has_active_dispute`,
`customer_opted_out`, risk flags) → next plan re-evaluates policy.

Unsupported spans are rejected. Prompt-injection text is untrusted
content, not instructions.

---

## APIs

| Method | Path | Effect |
|---|---|---|
| `POST` | `/api/agent/cases/{case_id}/plan` | Policy, model, recommendation, explanations. No execution. |
| `POST` | `/api/agent/cases/{case_id}/execute` | One validated simulated attempt. |
| `GET` | `/api/agent/runs/{agent_run_id}` | Full trace. |
| `GET` | `/api/recovery-cases/{case_id}/explanation` | `mode=deterministic` or `mode=llm` (falls back). |
| `POST` | `/api/recovery-cases/{case_id}/ask` | Constrained Q&A. Says when the record is insufficient. |
| `POST` | `/api/recovery-cases/{case_id}/extract` | Proposal; `apply=true` only after validation. |

---

## Fallback behavior

If Claude is disabled, unconfigured, slow, or invalid: deterministic
copy is returned and `source` is `deterministic`. The core product does
not break. Economic rankings never change because of language output.
