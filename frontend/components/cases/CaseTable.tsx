import Link from "next/link";

import { formatLiftPp, formatPaiseINR, formatRatio } from "@/lib/format/money";
import { actionLabel, policyStatusLabel } from "@/lib/format/policy";
import { withRun } from "@/lib/run";
import type { RecoveryCase } from "@/types/api";

function hasAnalysis(row: RecoveryCase): boolean {
  return row.model_analysis != null && Number.isInteger(
    row.model_analysis.expected_incremental_recovery_paise,
  );
}

function policyNote(row: RecoveryCase): string {
  if (row.blocked_actions.includes("attempt_manual_charge")) {
    return "Manual charge blocked";
  }
  if (row.allowed_actions.includes("attempt_manual_charge")) {
    return "Manual charge allowed";
  }
  return "Link / no action only";
}

export function CaseTable({
  cases,
  runId,
}: {
  cases: RecoveryCase[];
  runId: string;
}) {
  const ranked = cases.some(hasAnalysis);
  const rows = [...cases].sort((a, b) => {
    if (ranked) {
      const evA = a.model_analysis?.expected_incremental_recovery_paise ?? Number.NEGATIVE_INFINITY;
      const evB = b.model_analysis?.expected_incremental_recovery_paise ?? Number.NEGATIVE_INFINITY;
      if (evB !== evA) return evB - evA;
    }
    return b.backlog_amount_paise - a.backlog_amount_paise;
  });

  return (
    <div className="overflow-x-auto rounded-md border border-line bg-paper-raised">
      <table className="w-full min-w-[860px] table-fixed border-collapse text-left text-sm">
        <colgroup>
          <col className="w-[22%]" />
          <col className="w-[12%]" />
          <col className="w-[10%]" />
          <col className="w-[14%]" />
          <col className="w-[16%]" />
          <col className="w-[16%]" />
          <col className="w-[10%]" />
        </colgroup>
        <thead>
          <tr className="border-b border-line bg-sand/40 text-[11px] uppercase tracking-[0.1em] text-ink-soft">
            <th className="px-4 py-3 font-medium">Customer</th>
            <th className="px-3 py-3 text-right font-medium">Backlog</th>
            <th className="px-3 py-3 text-right font-medium">Lift</th>
            <th className="px-3 py-3 text-right font-medium">Incr. recovery</th>
            <th className="px-3 py-3 font-medium">Action</th>
            <th className="px-3 py-3 font-medium">Policy</th>
            <th className="px-4 py-3 text-right font-medium">Hist. success</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => {
            const analysis = row.model_analysis;
            return (
              <tr key={row.case_id} className="border-b border-line/70 last:border-b-0">
                <td className="px-4 py-3 align-middle">
                  <Link
                    href={withRun(`/cases/${row.case_id}`, runId)}
                    className="block truncate font-medium text-ink hover:text-forest"
                  >
                    {row.customer_name || row.customer_id}
                  </Link>
                  <p className="mt-0.5 truncate font-mono text-[11px] text-ink-soft">
                    {row.subscription_id}
                  </p>
                </td>
                <td className="px-3 py-3 text-right align-middle font-mono tabular whitespace-nowrap">
                  {formatPaiseINR(row.backlog_amount_paise)}
                </td>
                <td className="px-3 py-3 text-right align-middle font-mono tabular whitespace-nowrap">
                  {analysis ? formatLiftPp(analysis.estimated_uplift) : "—"}
                </td>
                <td className="px-3 py-3 text-right align-middle font-mono tabular whitespace-nowrap">
                  {analysis
                    ? formatPaiseINR(analysis.expected_incremental_recovery_paise)
                    : "—"}
                </td>
                <td className="px-3 py-3 align-middle capitalize">
                  <span className="block truncate">
                    {analysis ? actionLabel(analysis.selected_action) : "—"}
                  </span>
                </td>
                <td className="px-3 py-3 align-middle">
                  <p className="font-medium leading-5">
                    {policyStatusLabel(row.policy_status)}
                  </p>
                  <p className="mt-0.5 truncate text-[11px] leading-4 text-ink-soft">
                    {policyNote(row)}
                  </p>
                </td>
                <td className="px-4 py-3 text-right align-middle font-mono tabular whitespace-nowrap">
                  {formatRatio(row.historical_payment_success_rate)}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
