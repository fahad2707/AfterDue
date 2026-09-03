import { provenanceTone, StatusBadge } from "@/components/ui/Badge";
import { PageHeader } from "@/components/ui/MetricCard";
import { provenanceLabel } from "@/lib/format/policy";
import type { PolicyConfig } from "@/types/api";

export function PolicyInspector({ config }: { config: PolicyConfig }) {
  return (
    <div className="space-y-8">
      <PageHeader
        eyebrow="Deterministic safety"
        title="Policy"
        body="AI does not define payment safety. Deterministic policy does. These rules are evaluated before ranking or language can act. Provenance tells you whether a block comes from documented platform behavior, a product design assumption, or a safety guardrail."
      />
      <p className="font-mono text-xs text-ink-soft">Version {config.policy_version}</p>

      <div className="space-y-4">
        {config.rules.map((rule) => (
          <article
            key={rule.rule_id}
            className="rounded-lg border border-line bg-paper-raised p-5"
            data-testid="policy-rule"
            data-provenance={rule.provenance}
          >
            <div className="flex flex-wrap items-start justify-between gap-3">
              <h3 className="font-mono text-sm">{rule.rule_id}</h3>
              <StatusBadge tone={provenanceTone(rule.provenance)}>
                {provenanceLabel(rule.provenance)}
              </StatusBadge>
            </div>
            <p className="mt-3 text-sm text-ink-soft">{rule.condition}</p>
            <p className="mt-2 text-sm font-medium">{rule.effect}</p>
            <p className="mt-3 font-mono text-xs text-ink-soft">{rule.reason_code}</p>
            {rule.source_url ? (
              <a
                href={rule.source_url}
                className="mt-3 inline-block text-xs text-forest underline-offset-2 hover:underline"
                target="_blank"
                rel="noreferrer"
              >
                {rule.source_url}
              </a>
            ) : (
              <p className="mt-3 text-xs text-ink-soft">No source URL recorded.</p>
            )}
          </article>
        ))}
      </div>
    </div>
  );
}
