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
    <div className="overflow-x-auto">
      <table className="w-full min-w-[1080px] text-left text-sm">
        <thead>
          <tr className="border-b border-line text-[11px] uppercase tracking-[0.12em] text-ink-soft">
            <th className="py-2 font-medium">Customer</th>
            <th className="py-2 font-medium">Backlog</th>
            <th className="py-2 font-medium">Estimated lift</th>
            <th className="py-2 font-medium">Expected incremental recovery</th>
            <th className="py-2 font-medium">Recommended action</th>
            <th className="py-2 font-medium">Policy</th>
            <th className="py-2 font-medium">Historical success</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => {
            const analysis = row.model_analysis;
            return (
              <tr key={row.case_id} className="border-b border-line/70">
                <td className="py-3 align-top">
                  <Link
                    href={withRun(`/cases/${row.case_id}`, runId)}
                    className="font-medium text-ink hover:text-forest"
                  >
                    {row.customer_name || row.customer_id}
                  </Link>
                  <p className="mt-0.5 font-mono text-[11px] text-ink-soft">
                    {row.subscription_id}
                  </p>
                </td>
                <td className="py-3 align-top font-mono tabular">
                  {formatPaiseINR(row.backlog_amount_paise)}
                </td>
                <td className="py-3 align-top font-mono tabular">
                  {analysis ? formatLiftPp(analysis.estimated_uplift) : "—"}
                </td>
                <td className="py-3 align-top font-mono tabular">
                  {analysis
                    ? formatPaiseINR(analysis.expected_incremental_recovery_paise)
                    : "—"}
                </td>
                <td className="py-3 align-top capitalize">
                  {analysis ? actionLabel(analysis.selected_action) : "—"}
                  {analysis?.selected_action === "no_action" ? (
                    <p className="mt-1 text-[11px] leading-4 text-ink-soft">
                      Model ranking chose no intervention
                    </p>
                  ) : null}
                </td>
                <td className="py-3 align-top">
                  <p className="text-xs font-medium">
                    {policyStatusLabel(row.policy_status)}
                  </p>
                  <p className="mt-1 max-w-xs text-[11px] leading-4 text-ink-soft">
                    {row.blocked_actions.includes("attempt_manual_charge")
                      ? "Manual charge blocked by policy"
                      : row.allowed_actions.includes("attempt_manual_charge")
                        ? "Manual charge allowed"
                        : "Payment link / no action only"}
                  </p>
                </td>
                <td className="py-3 align-top font-mono tabular">
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
