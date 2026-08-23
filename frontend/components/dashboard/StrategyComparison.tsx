import { formatCount, formatPaiseINR, formatRatio } from "@/lib/format/money";
import { strategyLabel } from "@/lib/format/policy";
import type { StrategyMetrics } from "@/types/api";

const ORDER = ["naive", "rule_based", "reclaim"];

export function StrategyComparison({
  results,
}: {
  results: Record<string, StrategyMetrics>;
}) {
  const rows = ORDER.map((key) => results[key]).filter(Boolean);
  const max = Math.max(...rows.map((row) => row.revenue_recovered_paise), 1);

  return (
    <section data-testid="strategy-comparison">
      <h3 className="text-[11px] uppercase tracking-[0.14em] text-ink-soft">
        Strategy comparison
      </h3>
      <p className="mt-1 max-w-2xl text-sm text-ink-soft">
        Different decision strategies produce different recovery economics on the
        same synthetic world, policy, budget, and oracle.
      </p>

      <div className="mt-4 space-y-3">
        {rows.map((row) => {
          const width = Math.max(6, (row.revenue_recovered_paise / max) * 100);
          return (
            <div key={row.strategy_name}>
              <div className="mb-1 flex items-baseline justify-between gap-3">
                <span className="text-sm font-medium">
                  {strategyLabel(row.strategy_name)}
                </span>
                <span className="font-mono text-sm tabular">
                  {formatPaiseINR(row.revenue_recovered_paise)}
                </span>
              </div>
              <div className="h-2 rounded-sm bg-sand">
                <div
                  className="h-2 rounded-sm bg-forest"
                  style={{ width: `${width}%` }}
                />
              </div>
            </div>
          );
        })}
      </div>

      <div className="mt-6 overflow-x-auto">
        <table className="w-full min-w-[640px] text-left text-sm">
          <thead>
            <tr className="border-b border-line text-[11px] uppercase tracking-[0.12em] text-ink-soft">
              <th className="py-2 font-medium">Strategy</th>
              <th className="py-2 font-medium">Revenue recovered</th>
              <th className="py-2 font-medium">Yield</th>
              <th className="py-2 font-medium">Interventions</th>
              <th className="py-2 font-medium">Incremental</th>
              <th className="py-2 font-medium">Unnecessary</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr key={row.strategy_name} className="border-b border-line/70">
                <td className="py-2.5">{strategyLabel(row.strategy_name)}</td>
                <td className="py-2.5 font-mono tabular">
                  {formatPaiseINR(row.revenue_recovered_paise)}
                </td>
                <td className="py-2.5 font-mono tabular">
                  {formatRatio(row.recovery_yield)}
                </td>
                <td className="py-2.5 font-mono tabular">
                  {formatCount(row.interventions_used)}
                </td>
                <td className="py-2.5 font-mono tabular">
                  {formatPaiseINR(row.incremental_revenue_paise)}
                </td>
                <td className="py-2.5 font-mono tabular">
                  {formatCount(row.unnecessary_intervention_count)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}
