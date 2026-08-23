import { redirect } from "next/navigation";

import { Overview } from "@/components/dashboard/Overview";
import { EmptyState, ErrorState } from "@/components/ui/StateBlock";
import { apiGet } from "@/lib/server-api";
import { resolveRunId } from "@/lib/server-run";
import { withRun } from "@/lib/run";
import type { DashboardSummary } from "@/types/api";

export default async function Home({
  searchParams,
}: {
  searchParams: Promise<{ run?: string }>;
}) {
  const { run } = await searchParams;
  const runId = await resolveRunId(run);
  if (!run && runId) redirect(withRun("/", runId));
  if (!runId) {
    return (
      <EmptyState
        title="No simulation runs"
        body="Generate a synthetic world to see revenue at risk, recovery cases, and baseline comparison."
        href="/simulate"
        action="Open simulation"
      />
    );
  }

  const summary = await apiGet<DashboardSummary>(
    `/api/dashboard/summary?run_id=${encodeURIComponent(runId)}`,
  );
  if (!summary.ok) {
    if (summary.status === 404) {
      return (
        <EmptyState
          title="Run not found"
          body="That simulation run is not available. Generate a new world or pick another run."
          href="/simulate"
          action="Open simulation"
        />
      );
    }
    return (
      <ErrorState
        title="Dashboard could not be loaded"
        body="Backend is currently unavailable or the run summary failed to load."
      />
    );
  }

  return <Overview data={summary.data} />;
}
