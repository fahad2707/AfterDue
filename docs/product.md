# AfterDue — Product

AfterDue was previously developed under the internal codename RECLAIM.

AfterDue reconstructs historical unpaid invoices after post-halt
reactivation, validates which invoices represent collectible receivables,
and optimizes bounded recovery only over eligible debt.

When an active subscription is halted, leftover invoices can still be
issued. When the customer returns, Razorpay does not charge those unpaid
cycles automatically. The merchant has to collect that leftover revenue —
but only if it is actually collectible.

Invoice existence is not proof of collectibility. Halt-period invoices are
not automatically lost revenue, and they are not automatically recoverable
revenue.

This is a synthetic prototype for Razorpay AI Buildathon Track 03. It is
not an official Razorpay product.

## Pipeline

```
HALTED → ACTIVE
        ↓
historical invoice lineage
        ↓
unpaid invoices
        ↓
collectibility / service-entitlement gate
        ↓
        ├── COLLECTIBLE → recovery candidate → policy → ML → agent
        ├── NOT_COLLECTIBLE → excluded from recovery
        └── REVIEW_REQUIRED → no automatic recovery
```

Only collectible invoice value enters Recovery Case economics, policy,
uplift, incremental EV, intervention budget, and the bounded agent.

## Responsibilities

| Layer | Question |
|---|---|
| Collectibility | Is this receivable valid / eligible? |
| Policy | Given a valid receivable, what actions are allowed right now? |
| Model | Which allowed intervention changes expected recovery? |
| Agent | Execute that action safely. |

UNKNOWN service-delivery status fails closed to merchant review.
