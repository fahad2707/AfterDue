import { formatCount, formatPaiseINR } from "@/lib/format/money";

export function RevenueFunnel({
  historicalUnpaid,
  collectible,
  reviewRequired,
  excluded,
  cases,
  interventions,
  recovered,
}: {
  historicalUnpaid: number;
  collectible: number;
  reviewRequired: number;
  excluded: number;
  cases: number;
  interventions: number;
  recovered: number;
}) {
  const steps = [
    { label: "Historical unpaid invoices", value: formatPaiseINR(historicalUnpaid) },
    { label: "Collectible receivables", value: formatPaiseINR(collectible) },
    { label: "Review required", value: formatPaiseINR(reviewRequired) },
    { label: "Excluded / not collectible", value: formatPaiseINR(excluded) },
    { label: "Collectible recovery cases", value: formatCount(cases) },
    { label: "Interventions used", value: formatCount(interventions) },
    { label: "Recovered revenue", value: formatPaiseINR(recovered) },
  ];

  return (
    <section>
      <h3 className="text-[11px] uppercase tracking-[0.14em] text-ink-soft">
        Collectibility, then recovery
      </h3>
      <p className="mt-2 max-w-2xl text-sm leading-6 text-ink-soft">
        Invoice existence is not proof of collectibility. Excluded invoices are
        not lost revenue — service was not a valid receivable for those periods.
      </p>
      <ol className="mt-3 grid gap-2 sm:grid-cols-2 lg:grid-cols-4">
        {steps.map((step, index) => (
          <li
            key={step.label}
            className="rounded-md border border-line bg-paper-raised px-3 py-3"
          >
            <p className="font-mono text-[10px] text-ink-soft">{index + 1}</p>
            <p className="mt-2 text-xs text-ink-soft">{step.label}</p>
            <p className="mt-1 font-mono text-lg tabular text-ink">{step.value}</p>
          </li>
        ))}
      </ol>
    </section>
  );
}
