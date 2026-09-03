import Link from "next/link";

import { StatusBadge } from "@/components/ui/Badge";
import { formatLiftPp, formatPaiseINR } from "@/lib/format/money";
import { actionLabel, policyStatusLabel } from "@/lib/format/policy";
import { withRun } from "@/lib/run";
import type { RecoveryCase } from "@/types/api";

function statusTone(status: string): "info" | "attention" | "good" | "neutral" {
  if (status === "review_required") return "attention";
  if (status === "open") return "info";
  if (status === "closed") return "good";
  return "neutral";
}

function hasAnalysis(row: RecoveryCase): boolean {
  return row.model_analysis != null && Number.isInteger(
    row.model_analysis.expected_incremental_recovery_paise,
  );
}

function policyNote(row: RecoveryCase): string {
  if (row.status === "review_required") {
    return "Collectibility not established";
  }
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
    const collectibleA = a.collectible_amount_paise ?? a.backlog_amount_paise;
    const collectibleB = b.collectible_amount_paise ?? b.backlog_amount_paise;
    if (ranked) {
      const evA = a.model_analysis?.expected_incremental_recovery_paise ?? Number.NEGATIVE_INFINITY;
      const evB = b.model_analysis?.expected_incremental_recovery_paise ?? Number.NEGATIVE_INFINITY;
      if (evB !== evA) return evB - evA;
    }
    return collectibleB - collectibleA;
  });

  return (
    <div className="overflow-x-auto rounded-md border border-line bg-paper-raised" data-guide="case-table">
      <table className="w-full min-w-[1040px] table-fixed border-collapse text-left text-sm">
        <colgroup>
          <col className="w-[16%]" />
          <col className="w-[11%]" />
          <col className="w-[11%]" />
          <col className="w-[9%]" />
          <col className="w-[10%]" />
          <col className="w-[13%]" />
          <col className="w-[12%]" />
          <col className="w-[10%]" />
          <col className="w-[8%]" />
        </colgroup>
        <thead>
          <tr className="border-b border-line bg-sand/40 text-[11px] uppercase tracking-[0.1em] text-ink-soft">
            <th className="px-4 py-3 font-medium">Customer</th>
            <th className="px-3 py-3 text-right font-medium">Historical unpaid</th>
            <th className="px-3 py-3 text-right font-medium">Collectible</th>
            <th className="px-3 py-3 text-right font-medium">Review</th>
            <th className="px-3 py-3 text-right font-medium">Lift</th>
            <th className="px-3 py-3 text-right font-medium">Incr. recovery</th>
            <th className="px-3 py-3 font-medium">Action</th>
            <th className="px-4 py-3 font-medium">Policy</th>
            <th className="px-3 py-3 font-medium">Status</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => {
            const analysis = row.model_analysis;
            const historical = row.historical_unpaid_amount_paise ?? row.backlog_amount_paise;
            const collectible = row.collectible_amount_paise ?? row.backlog_amount_paise;
            const review = row.review_required_amount_paise ?? 0;
            const name = row.customer_name || row.customer_id;
            const href = withRun(`/cases/${row.case_id}`, runId);
            return (
              <tr
                key={row.case_id}
                className="case-row group cursor-pointer border-b border-line/70 last:border-b-0 hover:bg-sand/70"
              >
                <td className="px-4 py-3 align-middle">
                  <Link
                    href={href}
                    className="case-row-link block truncate font-medium text-ink group-hover:text-forest"
                    aria-label={`View recovery case details for ${name}`}
                  >
                    {name}
                  </Link>
                  <p className="pointer-events-none relative z-[3] mt-0.5 truncate font-mono text-[11px] text-ink-soft">
                    {row.subscription_id}
                  </p>
                  <p className="pointer-events-none relative z-[3] mt-1 text-[11px] font-medium text-forest opacity-0 transition-opacity group-hover:opacity-100 group-focus-within:opacity-100">
                    View case details
                  </p>
                </td>
                <td className="px-3 py-3 text-right align-middle figure whitespace-nowrap">
                  {formatPaiseINR(historical)}
                </td>
                <td className="px-3 py-3 text-right align-middle figure whitespace-nowrap">
                  {formatPaiseINR(collectible)}
                </td>
                <td className="px-3 py-3 text-right align-middle figure whitespace-nowrap">
                  {formatPaiseINR(review)}
                </td>
                <td className="px-3 py-3 text-right align-middle figure whitespace-nowrap">
                  {analysis ? formatLiftPp(analysis.estimated_uplift) : "—"}
                </td>
                <td className="px-3 py-3 text-right align-middle figure whitespace-nowrap">
                  {analysis
                    ? formatPaiseINR(analysis.expected_incremental_recovery_paise)
                    : "—"}
                </td>
                <td className="px-3 py-3 align-middle capitalize">
                  <span className="block truncate">
                    {analysis ? actionLabel(analysis.selected_action) : "—"}
                  </span>
                </td>
                <td className="px-4 py-3 align-middle">
                  <p className="font-medium leading-5">
                    {policyStatusLabel(row.policy_status)}
                  </p>
                  <p className="mt-0.5 truncate text-[11px] leading-4 text-ink-soft">
                    {policyNote(row)}
                  </p>
                </td>
                <td className="px-3 py-3 align-middle">
                  <StatusBadge tone={statusTone(row.status)}>
                    {row.status.replaceAll("_", " ")}
                  </StatusBadge>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
