import { explainCase } from "@/lib/format/explain";
import type { PolicyDecision, RecoveryCase } from "@/types/api";

export function WhyThisCase({
  caseRow,
  policy,
}: {
  caseRow: RecoveryCase;
  policy: PolicyDecision;
}) {
  const paragraphs = explainCase({
    invoiceCount: caseRow.invoice_count,
    backlogPaise: caseRow.backlog_amount_paise,
    reasonCodes: policy.reason_codes,
    allowedActions: policy.allowed_actions,
  });

  return (
    <section className="rounded-lg border border-line bg-sand/40 p-5">
      <h3 className="text-[11px] uppercase tracking-[0.14em] text-ink-soft">
        Why this case exists
      </h3>
      <div className="mt-3 space-y-3 text-sm leading-6 text-ink">
        {paragraphs.map((paragraph) => (
          <p key={paragraph}>{paragraph}</p>
        ))}
      </div>
    </section>
  );
}
