# RECLAIM — Policy v1

Deterministic financial safety boundary. No ML, no LLM, no execution.

Rules are typed Python in `backend/app/policy/rules_v1.py`. They are not a
YAML expression language. Versioning is the `v1` identifier on every decision.

Provenance values:

| Value | Meaning |
|---|---|
| `DOCUMENTED_PLATFORM_BEHAVIOR` | Independently verified against platform docs. |
| `PRODUCT_DESIGN_ASSUMPTION` | An explicit product choice we have not verified. |
| `SAFETY_GUARDRAIL` | Ours. Does not claim to describe Razorpay. |

No `source_url` is recorded unless we already hold a verified source.

---

## Actions

| Action | Kind |
|---|---|
| `no_action` | Always allowed. No rule may block doing nothing. |
| `send_payment_link` | Customer contact. Not executed in M2. |
| `attempt_manual_charge` | Automated collection. Not executed in M2. |
| `escalate_to_merchant` | Human handoff. Forced into the allowed set when any rule escalates. |

---

## Rules

### domestic_card_no_manual_charge

| | |
|---|---|
| Condition | `card_type == domestic` |
| Effect | Block `attempt_manual_charge`. `send_payment_link` stays eligible unless another rule blocks it. |
| Reason | `DOMESTIC_CARD_MANUAL_CHARGE_UNSUPPORTED` |
| Provenance | `DOCUMENTED_PLATFORM_BEHAVIOR` |
| Source | https://razorpay.com/docs/payments/subscriptions/payment-retries/ |

Verified against the live Razorpay Payment Retries page before M3. Under
"Manual Charge on Same Card" the page states, verbatim:

> Manual charging of a domestic card is not supported.

That is the precise rule: `attempt_manual_charge` is blocked when
`card_type == domestic`. `send_payment_link` is not mentioned there and stays
eligible. Mandate-cap remains a separate assumption.

### mandate_cap

| | |
|---|---|
| Condition | `backlog_amount_paise > mandate_max_amount_paise` |
| Effect | Block `attempt_manual_charge` |
| Reason | `MANDATE_CAP_EXCEEDED` |
| Provenance | `PRODUCT_DESIGN_ASSUMPTION` |
| Source | none |

Equality does not block. A backlog of ₹4,999 against a ₹4,999 mandate remains
chargeable under this rule.

Default `mandate_max_amount_paise` is the plan amount when the subscription is
created without an explicit cap.

### risk_flag

| | |
|---|---|
| Condition | `risk_flags` is non-empty |
| Effect | Block automated collection. Require escalation. |
| Reason | `RISK_FLAG_PRESENT` |
| Provenance | `SAFETY_GUARDRAIL` |
| Source | none |

Severity is not interpreted. One flag is enough.

### active_dispute

| | |
|---|---|
| Condition | `has_dispute == true` |
| Effect | STOP automated recovery. Allow `escalate_to_merchant` and `no_action`. |
| Reason | `ACTIVE_DISPUTE` |
| Provenance | `SAFETY_GUARDRAIL` |
| Source | none |

This is the only terminal STOP in v1. Later rules still contribute reason
codes; automated collection is stripped at the end.

### customer_opt_out

| | |
|---|---|
| Condition | `customer_opted_out == true` |
| Effect | Block `send_payment_link`. Require escalation. |
| Reason | `CUSTOMER_OPTED_OUT` |
| Provenance | `SAFETY_GUARDRAIL` |
| Source | none |

Does not, by itself, block `attempt_manual_charge`. That is deliberate: the
spec named contact, not collection. A later milestone can tighten this.

### max_attempts

| | |
|---|---|
| Condition | `attempt_count >= max_attempts` |
| Effect | Block automated collection. Require escalation. |
| Reason | `MAX_ATTEMPTS_REACHED` |
| Provenance | `SAFETY_GUARDRAIL` |
| Source | none |

Default `max_attempts` is 3 (`POLICY_MAX_ATTEMPTS`). No attempts are recorded
yet because M2 does not execute.

### contact_cooldown

| | |
|---|---|
| Condition | `last_contact_at` is set and `now - last_contact_at < contact_cooldown_hours` |
| Effect | Block `send_payment_link` |
| Reason | `CONTACT_COOLDOWN_ACTIVE` |
| Provenance | `SAFETY_GUARDRAIL` |
| Source | none |

`now` is injected. The engine never reads the wall clock. Default cooldown is
24 hours (`POLICY_CONTACT_COOLDOWN_HOURS`).

---

## Composition

Every applicable rule contributes. The final allowed set is the intersection
after all subtractions. A domestic card over the mandate cap with a risk flag
reports all three reason codes.

---

## Dry-run

`POST /api/policy/evaluate` accepts a hypothetical `PolicyContext` and returns
a `PolicyDecision`. It writes nothing. `GET /api/policy/config` returns the
version, the catalog, reason codes, and provenance — no secrets.
