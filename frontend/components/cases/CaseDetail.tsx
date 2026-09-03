import { AgentWorkbench } from "@/components/cases/AgentWorkbench";
import { AuditTimeline } from "@/components/cases/AuditTimeline";
import { BacklogTable } from "@/components/cases/BacklogTable";
import { CollectibilityPanel } from "@/components/cases/CollectibilityPanel";
import { LifecycleTimeline } from "@/components/cases/LifecycleTimeline";
import { ModelPanel } from "@/components/cases/ModelPanel";
import { PolicyPanel } from "@/components/cases/PolicyPanel";
import { WhyThisCase } from "@/components/cases/WhyThisCase";
import { StatusBadge } from "@/components/ui/Badge";
import { EmptyState } from "@/components/ui/StateBlock";
import { formatDate } from "@/lib/format/date";
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
  const historical = row.historical_unpaid_amount_paise ?? row.backlog_amount_paise;
  const collectible = row.collectible_amount_paise ?? row.backlog_amount_paise;

  return (
    <div className="space-y-8">
      <header>
        <p className="text-[11px] font-medium uppercase tracking-[0.16em] text-ink-soft">
          Recovery case
        </p>
        <h2 className="mt-2 text-3xl font-medium tracking-tight">{name}</h2>
        <p className="mt-1 font-mono text-xs text-ink-soft">{row.subscription_id}</p>
      </header>

      <section className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <div className="rounded-lg border border-line bg-paper-raised px-4 py-4">
          <p className="text-[11px] uppercase tracking-[0.12em] text-ink-soft">
            Historical unpaid
          </p>
          <p className="mt-2 font-medium text-2xl tabular">
            {formatPaiseINR(historical)}
          </p>
        </div>
        <div className="rounded-lg border border-forest/30 bg-paper-raised px-4 py-4">
          <p className="text-[11px] uppercase tracking-[0.12em] text-ink-soft">
            Collectible
          </p>
          <p className="mt-2 font-medium text-2xl tabular">
            {formatPaiseINR(collectible)}
          </p>
          <p className="mt-1 text-xs text-ink-soft">
            Only this amount enters recovery optimization
          </p>
        </div>
        <div className="rounded-lg border border-line bg-paper-raised px-4 py-4">
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
        <div className="rounded-lg border border-line bg-paper-raised px-4 py-4">
          <p className="text-[11px] uppercase tracking-[0.12em] text-ink-soft">
            Recovery window
          </p>
          <div className="mt-2">
            <StatusBadge
              tone={
                row.status === "review_required"
                  ? "attention"
                  : row.status === "closed"
                    ? "good"
                    : "info"
              }
            >
              {row.status.replaceAll("_", " ")}
            </StatusBadge>
          </div>
          <p className="mt-2 text-xs text-ink-soft">
            Simulated recovery is available below. No real payment is attempted.
          </p>
        </div>
      </section>

      <WhyThisCase caseRow={row} policy={detail.policy} />

      <section>
        <h3 className="mb-3 text-[11px] uppercase tracking-[0.14em] text-ink-soft">
          Why the case exists · subscription lifecycle
        </h3>
        <LifecycleTimeline
          caseRow={row}
          createdAt={detail.subscription_created_at}
          episodes={detail.halt_episodes}
        />
      </section>

      <section>
        <h3 className="mb-3 text-[11px] uppercase tracking-[0.14em] text-ink-soft">
          What historical debt exists
        </h3>
        {detail.invoices.length === 0 ? (
          <EmptyState title="No invoices" body="This case has no invoice records." />
        ) : (
          <BacklogTable
            invoices={detail.invoices}
            collectibleTotal={row.collectible_amount_paise ?? row.backlog_amount_paise}
          />
        )}
      </section>

      <CollectibilityPanel caseRow={row} invoices={detail.invoices} />
      <PolicyPanel policy={detail.policy} />
      <ModelPanel analysis={detail.model_analysis ?? row.model_analysis} />
      <AgentWorkbench detail={detail} />

      <section>
        <h3 className="mb-3 text-[11px] uppercase tracking-[0.14em] text-ink-soft">
          Audit trail
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
