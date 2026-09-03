import { collectibilityTone, StatusBadge } from "@/components/ui/Badge";
import { formatPaiseINR } from "@/lib/format/money";
import type { Invoice, RecoveryCase } from "@/types/api";

function reasonLabel(codes: string[] | undefined): string {
  if (!codes || codes.length === 0) return "—";
  return codes.join(", ").replaceAll("_", " ").toLowerCase();
}

export function CollectibilityPanel({
  caseRow,
  invoices,
}: {
  caseRow: RecoveryCase;
  invoices: Invoice[];
}) {
  const historical = caseRow.historical_unpaid_amount_paise ?? caseRow.backlog_amount_paise;
  const collectible = caseRow.collectible_amount_paise ?? caseRow.backlog_amount_paise;
  const excluded = caseRow.not_collectible_amount_paise ?? 0;
  const review = caseRow.review_required_amount_paise ?? 0;
  const delivered = invoices.filter((i) => i.service_delivery_status === "delivered").length;
  const suspended = invoices.filter((i) => i.service_delivery_status === "suspended").length;
  const unknown = invoices.filter(
    (i) => i.service_delivery_status === "unknown" || i.service_delivery_status === "partially_delivered",
  ).length;
  const bits: string[] = [];
  if (delivered) {
    bits.push(
      `${delivered} billing period${delivered === 1 ? "" : "s"} had confirmed service delivery.`,
    );
  }
  if (suspended) {
    bits.push(
      `${suspended} billing period${suspended === 1 ? "" : "s"} had service suspended.`,
    );
  }
  if (unknown) {
    bits.push(
      `${unknown} billing period${unknown === 1 ? "" : "s"} need merchant review.`,
    );
  }

  return (
    <section data-testid="collectibility-panel">
      <h3 className="mb-3 text-[11px] uppercase tracking-[0.14em] text-ink-soft">
        What is collectible
      </h3>
      <div className="rounded-lg border border-forest/25 bg-paper-raised px-4 py-5">
        <dl className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          <div className="rounded-md border border-line px-3 py-3">
            <dt className="text-[11px] uppercase tracking-[0.12em] text-ink-soft">
              Historical unpaid
            </dt>
            <dd className="mt-1 font-medium text-xl tabular">{formatPaiseINR(historical)}</dd>
          </div>
          <div className="rounded-md border border-good/25 bg-good/5 px-3 py-3">
            <dt className="text-[11px] uppercase tracking-[0.12em] text-ink-soft">
              Collectible
            </dt>
            <dd className="mt-1 font-medium text-xl tabular">{formatPaiseINR(collectible)}</dd>
            <dd className="mt-1">
              <StatusBadge tone="good">Enters optimization</StatusBadge>
            </dd>
          </div>
          <div className="rounded-md border border-stop/20 bg-stop/5 px-3 py-3">
            <dt className="text-[11px] uppercase tracking-[0.12em] text-ink-soft">
              Excluded
            </dt>
            <dd className="mt-1 font-medium text-xl tabular">{formatPaiseINR(excluded)}</dd>
            <dd className="mt-1">
              <StatusBadge tone="stop">Not a receivable</StatusBadge>
            </dd>
          </div>
          <div className="rounded-md border border-attention/20 bg-amber-soft/60 px-3 py-3">
            <dt className="text-[11px] uppercase tracking-[0.12em] text-ink-soft">
              Review required
            </dt>
            <dd className="mt-1 font-medium text-xl tabular">{formatPaiseINR(review)}</dd>
            <dd className="mt-1">
              <StatusBadge tone="attention">Not collectible yet</StatusBadge>
            </dd>
          </div>
        </dl>
        <p className="mt-4 text-sm leading-6 text-ink-soft">
          {bits.join(" ") || reasonLabel(invoices.flatMap((i) => i.collectibility_reason_codes ?? []))}
        </p>
        <p className="mt-2 text-sm leading-6 text-ink">
          Only {formatPaiseINR(collectible)} enters recovery optimization. Review-required
          money is not treated as collectible.
        </p>
        {invoices.length > 0 ? (
          <ul className="mt-4 space-y-2">
            {invoices.map((invoice) => (
              <li
                key={invoice.invoice_id}
                className="flex flex-wrap items-center justify-between gap-2 border-t border-line pt-2 text-sm"
              >
                <span className="font-mono text-xs">{invoice.billing_cycle}</span>
                <span className="font-medium tabular">{formatPaiseINR(invoice.amount_paise)}</span>
                <span className="capitalize text-ink-soft">
                  {(invoice.service_delivery_status ?? "unknown").replaceAll("_", " ")}
                </span>
                <StatusBadge tone={collectibilityTone(invoice.collectibility_status)}>
                  {(invoice.collectibility_status ?? "unknown").replaceAll("_", " ")}
                </StatusBadge>
              </li>
            ))}
          </ul>
        ) : null}
      </div>
    </section>
  );
}
