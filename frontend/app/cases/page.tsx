import { redirect } from "next/navigation";

import { CaseTable } from "@/components/cases/CaseTable";
import { EmptyState, ErrorState } from "@/components/ui/StateBlock";
import { apiGet } from "@/lib/server-api";
import { resolveRunId } from "@/lib/server-run";
import { withRun } from "@/lib/run";
import type { RecoveryCase } from "@/types/api";

export default async function CasesPage({
  searchParams,
}: {
  searchParams: Promise<{ run?: string }>;
}) {
  const { run } = await searchParams;
  const runId = await resolveRunId(run);
  if (!run && runId) redirect(withRun("/cases", runId));
  if (!runId) {
    return (
      <EmptyState
        title="No recovery cases"
        body="There is no selected run. Generate a synthetic world first."
        href="/simulate"
        action="Open simulation"
      />
    );
  }

  const result = await apiGet<RecoveryCase[]>(
    `/api/recovery-cases?run_id=${encodeURIComponent(runId)}`,
  );
  if (!result.ok) {
    return (
      <ErrorState
        title="Recovery queue unavailable"
        body="Backend is currently unavailable. Cases cannot be listed."
      />
    );
  }

  return (
    <div className="space-y-6">
      <header>
        <p className="font-mono text-[11px] uppercase tracking-[0.16em] text-ink-soft">
          {result.data.some((row) => row.model_analysis)
            ? "Sorted by expected incremental recovery"
            : "Sorted by backlog"}
        </p>
        <h2 className="mt-2 text-3xl font-medium tracking-tight">Recovery cases</h2>
        <p className="mt-2 max-w-2xl text-sm leading-6 text-ink-soft">
          Model ranking uses expected incremental recovery when an active
          model exists. Policy still decides which actions are eligible.
          Estimates are synthetic, not guaranteed recovery.
        </p>
      </header>
      {result.data.length === 0 ? (
        <EmptyState
          title="No recovery cases in this run"
          body="This world has no reactivated subscriptions with unpaid halt invoices."
        />
      ) : (
        <CaseTable cases={result.data} runId={runId} />
      )}
    </div>
  );
}
