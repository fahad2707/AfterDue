import { apiGet } from "@/lib/api/http";
import { scopedQuery } from "@/lib/run";
import type { AuditEntry, RecoveryCase, RecoveryCaseDetail } from "@/types/api";

export function listCases(runId: string) {
  return apiGet<RecoveryCase[]>(`/api/recovery-cases?${scopedQuery(runId)}`);
}

export function getCase(caseId: string) {
  return apiGet<RecoveryCaseDetail>(
    `/api/recovery-cases/${encodeURIComponent(caseId)}`,
  );
}

export function getCaseAudit(caseId: string) {
  return apiGet<AuditEntry[]>(
    `/api/recovery-cases/${encodeURIComponent(caseId)}/audit`,
  );
}
