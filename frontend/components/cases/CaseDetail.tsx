import { AuditTimeline } from "@/components/cases/AuditTimeline";
import { BacklogTable } from "@/components/cases/BacklogTable";
import { LifecycleTimeline } from "@/components/cases/LifecycleTimeline";
import { ModelPanel } from "@/components/cases/ModelPanel";
import { PolicyPanel } from "@/components/cases/PolicyPanel";
import { WhyThisCase } from "@/components/cases/WhyThisCase";
import { EmptyState } from "@/components/ui/StateBlock";
import { formatDate, formatDateRange } from "@/lib/format/date";
import { formatPaiseINR } from "@/lib/format/money";
import type { AuditEntry, RecoveryCaseDetail } from "@/types/api";

export function CaseDetailView({
  detail,
  audit,
}: {
  detail: RecoveryCaseDetail;
  audit: AuditEntry[];
}) {
  const row = detail.case;
  const name = detail.customer_name || row.customer_name || row.customer_id;

  return (
    <div className="space-y-8">
      <header>
        <p className="font-mono text-[11px] uppercase tracking-[0.16em] text-ink-soft">
          Recovery case
        </p>
        <h2 className="mt-2 text-3xl font-medium tracking-tight">{name}</h2>
        <p className="mt-1 font-mono text-xs text-ink-soft">{row.subscription_id}</p>
      </header>

      <section className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <div className="rounded-md border border-line bg-paper-raised px-4 py-4">
          <p className="text-[11px] uppercase tracking-[0.12em] text-ink-soft">
            Historical revenue at risk
          </p>
          <p className="mt-2 font-mono text-2xl tabular">
            {formatPaiseINR(row.backlog_amount_paise)}
          </p>
        </div>
        <div className="rounded-md border border-line bg-paper-raised px-4 py-4">
          <p className="text-[11px] uppercase tracking-[0.12em] text-ink-soft">
            Unpaid invoices
          </p>
          <p className="mt-2 font-mono text-2xl tabular">{row.invoice_count}</p>
          <p className="mt-1 text-xs text-ink-soft">
            {formatDateRange(row.oldest_invoice_at, row.newest_invoice_at)}
          </p>
        </div>
        <div className="rounded-md border border-line bg-paper-raised px-4 py-4">
          <p className="text-[11px] uppercase tracking-[0.12em] text-ink-soft">
            Subscription
          </p>
          <p className="mt-2 text-lg font-medium uppercase">
            {detail.subscription_status || "—"}
          </p>
          <p className="mt-1 text-xs text-ink-soft">
            Halted {formatDate(row.halted_at)}
          </p>
        </div>
        <div className="rounded-md border border-line bg-paper-raised px-4 py-4">
          <p className="text-[11px] uppercase tracking-[0.12em] text-ink-soft">
            Recovery window
          </p>
          <p className="mt-2 text-lg font-medium uppercase">{row.status}</p>
          <p className="mt-1 text-xs text-ink-soft">
            Observation only. No action is executed here.
          </p>
        </div>
      </section>

      <section>
        <h3 className="mb-3 text-[11px] uppercase tracking-[0.14em] text-ink-soft">
          Subscription lifecycle
        </h3>
        <LifecycleTimeline
          caseRow={row}
          createdAt={detail.subscription_created_at}
          episodes={detail.halt_episodes}
        />
      </section>

      <section>
        <h3 className="mb-3 text-[11px] uppercase tracking-[0.14em] text-ink-soft">
          Historical backlog
        </h3>
        {detail.invoices.length === 0 ? (
          <EmptyState title="No invoices" body="This case has no invoice records." />
        ) : (
          <BacklogTable invoices={detail.invoices} />
        )}
      </section>

      <ModelPanel analysis={detail.model_analysis ?? row.model_analysis} />
      <WhyThisCase caseRow={row} policy={detail.policy} />
      <PolicyPanel policy={detail.policy} />

      <section>
        <h3 className="mb-3 text-[11px] uppercase tracking-[0.14em] text-ink-soft">
          Audit timeline
        </h3>
        {audit.length === 0 ? (
          <EmptyState
            title="No audit records"
            body="There are no audit entries for this halt episode yet."
          />
        ) : (
          <AuditTimeline entries={audit} />
        )}
      </section>
    </div>
  );
}
