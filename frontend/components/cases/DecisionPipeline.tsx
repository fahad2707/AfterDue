import type { AuditEntry, ModelAnalysis, PolicyDecision, RecoveryCase } from "@/types/api";

const STAGES = [
  {
    id: "collectibility",
    title: "Collectibility",
    definition: "Is this receivable valid?",
  },
  {
    id: "policy",
    title: "Policy",
    definition: "What are we allowed to do?",
  },
  {
    id: "model",
    title: "Model",
    definition: "What is likely under each permitted action?",
  },
  {
    id: "economics",
    title: "Economics",
    definition: "Does acting create incremental value?",
  },
  {
    id: "validator",
    title: "Validator",
    definition: "Is it still safe immediately before acting?",
  },
  {
    id: "execution",
    title: "Execution",
    definition: "What happened?",
  },
  {
    id: "audit",
    title: "Audit",
    definition: "Can we prove why?",
  },
] as const;

function hasEvent(audit: AuditEntry[], needle: string): boolean {
  return audit.some((entry) => entry.event_type.includes(needle));
}

function stageDone(
  id: (typeof STAGES)[number]["id"],
  caseRow: RecoveryCase,
  policy: PolicyDecision,
  analysis: ModelAnalysis | null | undefined,
  audit: AuditEntry[],
): boolean {
  if (id === "collectibility") {
    return (
      caseRow.collectible_amount_paise != null ||
      caseRow.collectibility_status != null ||
      Boolean(caseRow.invoice_count)
    );
  }
  if (id === "policy") return Boolean(policy.policy_version);
  if (id === "model") return analysis != null;
  if (id === "economics") {
    return analysis?.expected_incremental_recovery_paise != null;
  }
  if (id === "validator") {
    return (
      hasEvent(audit, "ACTION_VALIDAT") ||
      hasEvent(audit, "POLICY_REVALIDATED") ||
      hasEvent(audit, "ACTION_BLOCKED")
    );
  }
  if (id === "execution") {
    return (
      hasEvent(audit, "ACTION_EXECUTED") ||
      hasEvent(audit, "OUTCOME_OBSERVED") ||
      caseRow.amount_recovered_paise > 0
    );
  }
  return audit.length > 0;
}

export function DecisionPipeline({
  caseRow,
  policy,
  analysis,
  audit,
}: {
  caseRow: RecoveryCase;
  policy: PolicyDecision;
  analysis: ModelAnalysis | null | undefined;
  audit: AuditEntry[];
}) {
  return (
    <section>
      <h3 className="mb-3 text-[11px] uppercase tracking-[0.14em] text-ink-soft">
        Decision pipeline
      </h3>
      <ol className="pipeline-track grid gap-2 lg:grid-cols-7">
        {STAGES.map((stage, index) => {
          const done = stageDone(stage.id, caseRow, policy, analysis, audit);
          return (
            <li
              key={stage.id}
              className="ad-stagger rounded-md border border-line bg-paper-raised px-3 py-3"
              style={{ animationDelay: `${index * 45}ms` }}
            >
              <p className="flex items-center gap-2 text-[11px] font-medium uppercase tracking-[0.12em]">
                <span
                  className={`inline-flex h-4 w-4 items-center justify-center rounded-full text-[10px] ${
                    done
                      ? "bg-good-soft text-good"
                      : "bg-sand text-ink-soft"
                  }`}
                  aria-hidden="true"
                >
                  {done ? "✓" : index + 1}
                </span>
                <span className={done ? "text-ink" : "text-ink-soft"}>
                  {stage.title}
                </span>
              </p>
              <p className="mt-2 text-xs leading-5 text-ink-soft">{stage.definition}</p>
              <p className="mt-2 text-[10px] uppercase tracking-[0.12em] text-ink-soft">
                {done ? "Complete" : "Pending"}
              </p>
            </li>
          );
        })}
      </ol>
    </section>
  );
}
