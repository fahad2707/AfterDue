import { provenanceLabel } from "@/lib/format/policy";
import type { PolicyConfig } from "@/types/api";

export function PolicyInspector({ config }: { config: PolicyConfig }) {
  return (
    <div className="space-y-8">
      <header>
        <p className="font-mono text-[11px] uppercase tracking-[0.16em] text-ink-soft">
          Deterministic safety
        </p>
        <h2 className="mt-2 text-3xl font-medium tracking-tight">Policy</h2>
        <p className="mt-2 max-w-2xl text-sm leading-6 text-ink-soft">
          AI does not define payment safety. Deterministic policy does. These
          rules are evaluated before any later ranking or language layer can
          act.
        </p>
        <p className="mt-3 font-mono text-xs">Version {config.policy_version}</p>
      </header>

      <div className="space-y-4">
        {config.rules.map((rule) => (
          <article
            key={rule.rule_id}
            className="rounded-md border border-line bg-paper-raised p-5"
            data-testid="policy-rule"
            data-provenance={rule.provenance}
          >
            <h3 className="font-mono text-sm">{rule.rule_id}</h3>
            <p className="mt-2 text-sm text-ink-soft">{rule.condition}</p>
            <p className="mt-1 text-sm">{rule.effect}</p>
            <p className="mt-3 font-mono text-xs">{rule.reason_code}</p>
            <p
              className={`mt-2 text-sm ${
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
                className="mt-2 inline-block text-xs text-forest underline-offset-2 hover:underline"
                target="_blank"
                rel="noreferrer"
              >
                {rule.source_url}
              </a>
            ) : (
              <p className="mt-2 text-xs text-ink-soft">No source URL recorded.</p>
            )}
          </article>
        ))}
      </div>
    </div>
  );
}
