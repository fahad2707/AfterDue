import Link from "next/link";

import { formatPaiseINR, formatRatio } from "@/lib/format/money";
import { actionLabel, policyStatusLabel } from "@/lib/format/policy";
import { withRun } from "@/lib/run";
import type { RecoveryCase } from "@/types/api";

export function CaseTable({
  cases,
  runId,
}: {
  cases: RecoveryCase[];
  runId: string;
}) {
  const rows = [...cases].sort(
    (a, b) => b.backlog_amount_paise - a.backlog_amount_paise,
  );

  return (
    <div className="overflow-x-auto">
      <table className="w-full min-w-[920px] text-left text-sm">
        <thead>
          <tr className="border-b border-line text-[11px] uppercase tracking-[0.12em] text-ink-soft">
            <th className="py-2 font-medium">Customer</th>
            <th className="py-2 font-medium">Backlog</th>
            <th className="py-2 font-medium">Invoices</th>
            <th className="py-2 font-medium">Halt</th>
            <th className="py-2 font-medium">Card</th>
            <th className="py-2 font-medium">Historical success</th>
            <th className="py-2 font-medium">Policy</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
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
              <td className="py-3 align-top font-mono tabular">{row.invoice_count}</td>
              <td className="py-3 align-top font-mono tabular">
                {row.halt_duration_days} days
              </td>
              <td className="py-3 align-top capitalize">{row.card_type}</td>
              <td className="py-3 align-top font-mono tabular">
                {formatRatio(row.historical_payment_success_rate)}
              </td>
              <td className="py-3 align-top">
                <p className="text-xs font-medium">
                  {policyStatusLabel(row.policy_status)}
                </p>
                <p className="mt-1 max-w-xs text-[11px] leading-4 text-ink-soft">
                  {row.allowed_actions.includes("send_payment_link")
                    ? "Payment link allowed"
                    : "Payment link blocked"}
                  {" · "}
                  {row.blocked_actions.includes("attempt_manual_charge")
                    ? "Manual charge blocked"
                    : row.allowed_actions.includes("attempt_manual_charge")
                      ? "Manual charge allowed"
                      : actionLabel(row.allowed_actions[0] ?? "no_action")}
                </p>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
