import Link from "next/link";

import { RevenueFunnel } from "@/components/dashboard/RevenueFunnel";
import { StrategyComparison } from "@/components/dashboard/StrategyComparison";
import { EmptyState } from "@/components/ui/StateBlock";
import { formatCount, formatPaiseINR, formatRatio } from "@/lib/format/money";
import { strategyLabel } from "@/lib/format/policy";
import { withRun } from "@/lib/run";
import type { DashboardSummary } from "@/types/api";

function Card({
  label,
  value,
  hint,
}: {
  label: string;
  value: string;
  hint?: string;
}) {
  return (
    <div className="rounded-md border border-line bg-paper-raised px-4 py-4">
      <p className="text-[11px] uppercase tracking-[0.14em] text-ink-soft">{label}</p>
      <p className="mt-2 font-mono text-2xl tabular tracking-tight text-ink">{value}</p>
      {hint ? <p className="mt-1 text-xs text-ink-soft">{hint}</p> : null}
    </div>
  );
}

export function Overview({ data }: { data: DashboardSummary }) {
  const strategies = Object.values(data.strategy_results ?? {});
  const best = data.best_baseline_name
    ? data.strategy_results[data.best_baseline_name]
    : undefined;
  const recovered = best?.revenue_recovered_paise ?? 0;
  const used = best?.interventions_used ?? 0;

  return (
    <div className="space-y-8">
      <header>
        <p className="font-mono text-[11px] uppercase tracking-[0.18em] text-ink-soft">
          Revenue Recovery OS
        </p>
        <h2 className="mt-2 text-3xl font-medium tracking-tight">RECLAIM</h2>
        <p className="mt-2 max-w-xl text-sm leading-6 text-ink-soft">
          Recover historical subscription revenue after customers return.
        </p>
      </header>

      <section className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
        <Card
          label="Historical revenue at risk"
          value={formatPaiseINR(data.revenue_at_risk_paise)}
        />
        <Card label="Recovery cases" value={formatCount(data.recovery_case_count)} />
        <Card label="Reactivated customers" value={formatCount(data.reactivated_count)} />
        <Card label="Intervention budget" value={formatCount(data.intervention_budget)} />
        <Card
          label="Best baseline recovery"
          value={
            data.best_baseline_recovery_paise == null
              ? "—"
              : formatPaiseINR(data.best_baseline_recovery_paise)
          }
          hint={
            data.best_baseline_name
              ? strategyLabel(data.best_baseline_name)
              : "Run strategies on Simulation"
          }
        />
        <Card
          label="RECLAIM vs best baseline"
          value={
            data.reclaim_vs_best_baseline_paise == null
              ? "—"
              : formatPaiseINR(data.reclaim_vs_best_baseline_paise)
          }
          hint="Incremental recovered revenue vs Naive/Rule-based"
        />
        <Card
          label="Recovery yield"
          value={formatRatio(data.best_baseline_yield)}
        />
      </section>

      <RevenueFunnel
        atRisk={data.revenue_at_risk_paise}
        cases={data.recovery_case_count}
        interventions={used}
        recovered={recovered}
      />

      {strategies.length === 0 ? (
        <EmptyState
          title="Baselines have not been run"
          body="Generate a world, then run Naive, Rule-based, and RECLAIM on the same seed to compare recovery economics."
          href={withRun("/simulate", data.run_id)}
          action="Open simulation"
        />
      ) : (
        <StrategyComparison results={data.strategy_results} />
      )}

      <p className="text-sm">
        <Link
          href={withRun("/cases", data.run_id)}
          className="text-forest underline-offset-4 hover:underline"
        >
          Inspect the recovery queue
        </Link>
      </p>
    </div>
  );
}
