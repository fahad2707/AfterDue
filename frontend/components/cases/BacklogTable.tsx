import { formatMonth } from "@/lib/format/date";
import { formatPaiseINR } from "@/lib/format/money";
import type { Invoice } from "@/types/api";

export function BacklogTable({ invoices }: { invoices: Invoice[] }) {
  const rows = [...invoices].sort(
    (a, b) => new Date(a.period_start).getTime() - new Date(b.period_start).getTime(),
  );
  const total = rows.reduce((sum, invoice) => sum + invoice.amount_paise, 0);

  return (
    <div data-testid="backlog-table" className="overflow-x-auto">
      <table className="w-full min-w-[640px] text-left text-sm">
        <thead>
          <tr className="border-b border-line text-[11px] uppercase tracking-[0.12em] text-ink-soft">
            <th className="py-2 font-medium">Billing cycle</th>
            <th className="py-2 font-medium">Period</th>
            <th className="py-2 font-medium">Amount</th>
            <th className="py-2 font-medium">Status</th>
            <th className="py-2 font-medium">Halt episode</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((invoice) => (
            <tr key={invoice.invoice_id} className="border-b border-line/70">
              <td className="py-2.5 font-mono">{invoice.billing_cycle}</td>
              <td className="py-2.5">{formatMonth(invoice.period_start)}</td>
              <td className="py-2.5 font-mono tabular">
                {formatPaiseINR(invoice.amount_paise)}
              </td>
              <td className="py-2.5 capitalize">
                {invoice.status.replaceAll("_", " ")}
              </td>
              <td className="py-2.5">
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
          <tr>
            <td className="pt-3 text-sm font-medium" colSpan={2}>
              Total
            </td>
            <td className="pt-3 font-mono tabular" colSpan={3}>
              {formatPaiseINR(total)}
            </td>
          </tr>
        </tfoot>
      </table>
    </div>
  );
}
