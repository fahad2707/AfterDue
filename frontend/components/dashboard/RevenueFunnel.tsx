import { formatCount, formatPaiseINR } from "@/lib/format/money";

export function RevenueFunnel({
  atRisk,
  cases,
  interventions,
  recovered,
}: {
  atRisk: number;
  cases: number;
  interventions: number;
  recovered: number;
}) {
  const steps = [
    { label: "Historical revenue at risk", value: formatPaiseINR(atRisk) },
    { label: "Eligible recovery cases", value: formatCount(cases) },
    { label: "Interventions used", value: formatCount(interventions) },
    { label: "Revenue recovered", value: formatPaiseINR(recovered) },
  ];

  return (
    <section>
      <h3 className="text-[11px] uppercase tracking-[0.14em] text-ink-soft">
        Recovery path
      </h3>
      <ol className="mt-3 grid gap-2 sm:grid-cols-4">
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
