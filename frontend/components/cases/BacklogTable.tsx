import { collectibilityTone, StatusBadge } from "@/components/ui/Badge";
import { formatMonth } from "@/lib/format/date";
import { formatPaiseINR } from "@/lib/format/money";
import type { Invoice } from "@/types/api";

function statusLabel(value: string | undefined): string {
  if (!value) return "—";
  return value.replaceAll("_", " ");
}

export function BacklogTable({
  invoices,
  collectibleTotal,
}: {
  invoices: Invoice[];
  collectibleTotal?: number;
}) {
  const rows = [...invoices].sort(
    (a, b) => new Date(a.period_start).getTime() - new Date(b.period_start).getTime(),
  );
  const historical = rows.reduce((sum, invoice) => sum + invoice.amount_paise, 0);

  return (
    <div
      data-testid="backlog-table"
      className="overflow-x-auto rounded-md border border-line bg-paper-raised"
    >
      <table className="w-full min-w-[860px] table-fixed border-collapse text-left text-sm">
        <thead>
          <tr className="border-b border-line bg-sand/40 text-[11px] uppercase tracking-[0.1em] text-ink-soft">
            <th className="px-4 py-3 font-medium">Billing cycle</th>
            <th className="px-3 py-3 font-medium">Period</th>
            <th className="px-3 py-3 text-right font-medium">Amount</th>
            <th className="px-3 py-3 font-medium">Service</th>
            <th className="px-3 py-3 font-medium">Collectibility</th>
            <th className="px-4 py-3 font-medium">Reason</th>
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
              <td className="px-3 py-2.5 text-right figure whitespace-nowrap">
                {formatPaiseINR(invoice.amount_paise)}
              </td>
              <td className="px-3 py-2.5 capitalize">
                {statusLabel(invoice.service_delivery_status)}
              </td>
              <td className="px-3 py-2.5">
                <StatusBadge tone={collectibilityTone(invoice.collectibility_status)}>
                  {statusLabel(invoice.collectibility_status)}
                </StatusBadge>
              </td>
              <td className="px-4 py-2.5 text-xs text-ink-soft">
                {statusLabel(invoice.collectibility_reason_codes?.[0])}
              </td>
            </tr>
          ))}
        </tbody>
        <tfoot>
          <tr className="border-t border-line bg-sand/30">
            <td className="px-4 py-3 text-sm font-medium" colSpan={2}>
              Historical unpaid
            </td>
            <td className="px-3 py-3 text-right figure whitespace-nowrap">
              {formatPaiseINR(historical)}
            </td>
            <td colSpan={3} />
          </tr>
          {collectibleTotal != null ? (
            <tr className="bg-sand/30">
              <td className="px-4 py-3 text-sm font-medium" colSpan={2}>
                Collectible (enters optimization)
              </td>
              <td className="px-3 py-3 text-right figure whitespace-nowrap">
                {formatPaiseINR(collectibleTotal)}
              </td>
              <td colSpan={3} />
            </tr>
          ) : null}
        </tfoot>
      </table>
    </div>
  );
}
