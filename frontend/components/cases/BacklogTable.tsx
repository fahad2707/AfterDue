import { formatMonth } from "@/lib/format/date";
import { formatPaiseINR } from "@/lib/format/money";
import type { Invoice } from "@/types/api";

export function BacklogTable({ invoices }: { invoices: Invoice[] }) {
  const rows = [...invoices].sort(
    (a, b) => new Date(a.period_start).getTime() - new Date(b.period_start).getTime(),
  );
  const total = rows.reduce((sum, invoice) => sum + invoice.amount_paise, 0);

  return (
    <div
      data-testid="backlog-table"
      className="overflow-x-auto rounded-md border border-line bg-paper-raised"
    >
      <table className="w-full min-w-[640px] table-fixed border-collapse text-left text-sm">
        <thead>
          <tr className="border-b border-line bg-sand/40 text-[11px] uppercase tracking-[0.1em] text-ink-soft">
            <th className="px-4 py-3 font-medium">Billing cycle</th>
            <th className="px-3 py-3 font-medium">Period</th>
            <th className="px-3 py-3 text-right font-medium">Amount</th>
            <th className="px-3 py-3 font-medium">Status</th>
            <th className="px-4 py-3 font-medium">Halt episode</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((invoice) => (
            <tr key={invoice.invoice_id} className="border-b border-line/70 last:border-b-0">
              <td className="px-4 py-2.5 font-mono whitespace-nowrap">
                {invoice.billing_cycle}
              </td>
              <td className="px-3 py-2.5 whitespace-nowrap">
                {formatMonth(invoice.period_start)}
              </td>
              <td className="px-3 py-2.5 text-right font-mono tabular whitespace-nowrap">
                {formatPaiseINR(invoice.amount_paise)}
              </td>
              <td className="px-3 py-2.5 capitalize">
                {invoice.status.replaceAll("_", " ")}
              </td>
              <td className="px-4 py-2.5">
                <span className="font-mono text-xs">{invoice.halt_episode_id ?? "—"}</span>
                {invoice.generated_during_halt ? (
                  <span className="ml-2 text-[11px] uppercase tracking-[0.1em] text-amber">
                    Generated during halt
                  </span>
                ) : null}
              </td>
            </tr>
          ))}
        </tbody>
        <tfoot>
          <tr className="border-t border-line bg-sand/30">
            <td className="px-4 py-3 text-sm font-medium" colSpan={2}>
              Total
            </td>
            <td className="px-3 py-3 text-right font-mono tabular whitespace-nowrap">
              {formatPaiseINR(total)}
            </td>
            <td colSpan={2} />
          </tr>
        </tfoot>
      </table>
    </div>
  );
}
