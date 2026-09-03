import { redirect } from "next/navigation";

import { CaseTable } from "@/components/cases/CaseTable";
import { PageHeader } from "@/components/ui/MetricCard";
import { EmptyState, ErrorState } from "@/components/ui/StateBlock";
import { withRun } from "@/lib/run";
import { apiGet } from "@/lib/server-api";
import { resolveRunId } from "@/lib/server-run";
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
    <div className="space-y-8">
      <PageHeader
        eyebrow={
          result.data.some((row) => row.model_analysis)
            ? "Sorted by expected incremental recovery"
            : "Sorted by collectible amount"
        }
        title="Recovery Cases"
        body="Historical unpaid is not collectible revenue. Ranking uses expected incremental recovery when a model exists. Policy still decides which actions are eligible. Estimates are synthetic."
      />
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
