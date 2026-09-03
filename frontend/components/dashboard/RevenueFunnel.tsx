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
  const spine = [
    { label: "Historical unpaid", value: formatPaiseINR(historicalUnpaid), hint: "Invoice lineage after halt" },
    { label: "Collectible", value: formatPaiseINR(collectible), hint: "Service delivered" },
    { label: "Selected for intervention", value: formatCount(interventions), hint: `${formatCount(cases)} collectible cases` },
    { label: "Recovered", value: formatPaiseINR(recovered), hint: "Simulated, collectible only" },
  ];

  return (
    <section>
      <h3 className="text-[11px] font-medium uppercase tracking-[0.14em] text-ink-soft">
        How leftover revenue is treated
      </h3>
      <p className="mt-2 max-w-2xl text-sm leading-6 text-ink-soft">
        Historical unpaid is not collectible revenue. Review {formatPaiseINR(reviewRequired)}{" "}
        and excluded {formatPaiseINR(excluded)} never enter optimization.
      </p>
      <ol className="mt-4 grid gap-2 sm:grid-cols-2 lg:grid-cols-4">
        {spine.map((step, index) => (
          <li
            key={step.label}
            className="rounded-lg border border-line bg-paper-raised px-3 py-3"
          >
            <p className="font-mono text-[10px] text-ink-soft">{index + 1}</p>
            <p className="mt-2 text-xs text-ink-soft">{step.label}</p>
            <p className="mt-1 font-medium text-lg tabular text-ink">{step.value}</p>
            <p className="mt-1 text-[11px] text-ink-soft">{step.hint}</p>
          </li>
        ))}
      </ol>
    </section>
  );
}
