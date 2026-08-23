import { actionLabel, provenanceLabel } from "@/lib/format/policy";
import type { PolicyDecision } from "@/types/api";

export function PolicyPanel({ policy }: { policy: PolicyDecision }) {
  return (
    <section className="rounded-md border border-line bg-paper-raised p-5">
      <div className="flex items-baseline justify-between gap-3">
        <h3 className="text-[11px] uppercase tracking-[0.14em] text-ink-soft">
          Policy decision
        </h3>
        <p className="font-mono text-xs">Version {policy.policy_version}</p>
      </div>

      <div className="mt-4 grid gap-4 sm:grid-cols-2">
        <div>
          <p className="text-[11px] uppercase tracking-[0.12em] text-ink-soft">
            Allowed actions
          </p>
          <ul className="mt-2 space-y-1 font-mono text-sm">
            {policy.allowed_actions.map((action) => (
              <li key={action}>{actionLabel(action)}</li>
            ))}
          </ul>
        </div>
        <div>
          <p className="text-[11px] uppercase tracking-[0.12em] text-ink-soft">
            Blocked actions
          </p>
          <ul className="mt-2 space-y-1 font-mono text-sm">
            {policy.blocked_actions.length === 0 ? (
              <li className="text-ink-soft">None</li>
            ) : (
              policy.blocked_actions.map((action) => <li key={action}>{actionLabel(action)}</li>)
            )}
          </ul>
        </div>
      </div>

      <div className="mt-5 space-y-3">
        {policy.applied_rules.length === 0 ? (
          <p className="text-sm text-ink-soft">No restricting rules applied.</p>
        ) : (
          policy.applied_rules.map((rule) => (
            <div key={`${rule.rule_id}-${rule.reason_code}`} className="border-t border-line pt-3">
              <p className="font-mono text-xs">{rule.reason_code}</p>
              <p
                className={`mt-1 text-sm ${
                  rule.provenance === "PRODUCT_DESIGN_ASSUMPTION"
                    ? "text-attention"
                    : "text-ink"
                }`}
              >
                {provenanceLabel(rule.provenance)}
              </p>
              {rule.source_url ? (
                <a
                  href={rule.source_url}
                  className="mt-1 inline-block text-xs text-forest underline-offset-2 hover:underline"
                  target="_blank"
                  rel="noreferrer"
                >
                  {rule.source_url}
                </a>
              ) : null}
            </div>
          ))
        )}
      </div>
    </section>
  );
}
