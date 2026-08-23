import { CaseDetailView } from "@/components/cases/CaseDetail";
import { EmptyState, ErrorState } from "@/components/ui/StateBlock";
import { apiGet } from "@/lib/server-api";
import type { AuditEntry, RecoveryCaseDetail } from "@/types/api";

export default async function CasePage({
  params,
}: {
  params: Promise<{ caseId: string }>;
}) {
  const { caseId } = await params;
  const [detail, audit] = await Promise.all([
    apiGet<RecoveryCaseDetail>(`/api/recovery-cases/${encodeURIComponent(caseId)}`),
    apiGet<AuditEntry[]>(`/api/recovery-cases/${encodeURIComponent(caseId)}/audit`),
  ]);

  if (!detail.ok) {
    if (detail.status === 404) {
      return (
        <EmptyState
          title="Case not found"
          body="This recovery case does not exist or belongs to another run."
          href="/cases"
          action="Back to queue"
        />
      );
    }
    return (
      <ErrorState
        title="Case could not be loaded"
        body="Backend is currently unavailable."
      />
    );
  }

  return <CaseDetailView detail={detail.data} audit={audit.ok ? audit.data : []} />;
}
