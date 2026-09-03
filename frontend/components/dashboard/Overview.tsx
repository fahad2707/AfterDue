import Link from "next/link";

import { RevenueFunnel } from "@/components/dashboard/RevenueFunnel";
import { StrategyComparison } from "@/components/dashboard/StrategyComparison";
import { EmptyState } from "@/components/ui/StateBlock";
import { MetricCard, PageHeader } from "@/components/ui/MetricCard";
import { SyntheticBadge } from "@/components/console/SyntheticBadge";
import { formatCount, formatPaiseINR, formatRatio } from "@/lib/format/money";
import { strategyLabel } from "@/lib/format/policy";
import { withRun } from "@/lib/run";
import type { DashboardSummary } from "@/types/api";

export function Overview({ data }: { data: DashboardSummary }) {
  const strategies = Object.values(data.strategy_results ?? {});
  const best = data.best_baseline_name
    ? data.strategy_results[data.best_baseline_name]
    : undefined;
  const recovered = best?.revenue_recovered_paise ?? 0;
  const used = best?.interventions_used ?? 0;
  const historical =
    data.historical_unpaid_amount_paise ?? data.revenue_at_risk_paise;
  const collectible = data.collectible_amount_paise ?? data.revenue_at_risk_paise;
  const review = data.review_required_amount_paise ?? 0;
  const excluded = data.not_collectible_amount_paise ?? 0;
  const yieldDenom = collectible || data.revenue_at_risk_paise;
  const yieldValue =
    yieldDenom > 0 && data.best_baseline_recovery_paise != null
      ? data.best_baseline_recovery_paise / yieldDenom
      : data.best_baseline_yield;
  const afterDue = data.strategy_results?.reclaim;

  return (
    <div className="space-y-8">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <PageHeader
          eyebrow="Overview"
          title="AfterDue"
          body="When a halted subscription returns to active, leftover unpaid invoices are not charged automatically. AfterDue reconstructs that history, validates collectible receivables, then ranks bounded interventions."
        />
        <SyntheticBadge />
      </div>

      <section data-guide="overview-metrics">
        <h3 className="text-[11px] font-medium uppercase tracking-[0.14em] text-ink-soft">
          Leftover revenue funnel
        </h3>
        <p className="mt-1 max-w-2xl text-sm leading-6 text-ink-soft">
          Raw historical unpaid is not recoverable opportunity. Review and excluded
          amounts leave the funnel before optimization.
        </p>
        <div className="mt-4 grid gap-px overflow-hidden rounded-md border border-line bg-line sm:grid-cols-2 xl:grid-cols-4">
          <MetricCard label="Historical unpaid" value={formatPaiseINR(historical)} />
          <MetricCard
            label="Collectible"
            value={formatPaiseINR(collectible)}
            hint="Eligible for recovery optimization"
            tone="good"
            emphasize
          />
          <MetricCard
            label="Review required"
            value={formatPaiseINR(review)}
            hint="Not collectible yet"
            tone="attention"
          />
          <MetricCard
            label="Excluded"
            value={formatPaiseINR(excluded)}
            hint="Not a valid receivable"
            tone="excluded"
          />
        </div>
      </section>

      <section className="rounded-md border border-line bg-paper-raised px-4 py-4">
        <h3 className="text-[11px] font-medium uppercase tracking-[0.14em] text-ink-soft">
          What AfterDue is doing right now
        </h3>
        <dl className="mt-3 grid gap-3 sm:grid-cols-3">
          <div>
            <dd className="figure text-lg font-medium">
              {formatCount(data.collectible_recovery_case_count ?? data.recovery_case_count)}
            </dd>
            <dt className="mt-1 text-xs text-ink-soft">Collectible cases in queue</dt>
          </div>
          <div>
            <dd className="figure text-lg font-medium">
              {formatCount(data.review_required_case_count ?? 0)}
            </dd>
            <dt className="mt-1 text-xs text-ink-soft">Review-required cases</dt>
          </div>
          <div>
            <dd className="figure text-lg font-medium">
              {formatCount(used)} / {formatCount(data.intervention_budget)}
            </dd>
            <dt className="mt-1 text-xs text-ink-soft">Interventions used</dt>
          </div>
        </dl>
        <p className="mt-3 text-sm text-ink-soft">
          {afterDue
            ? "AfterDue has already been run on this synthetic world. Inspect cases for collectibility, policy, and simulated execution."
            : "Strategies have not been run yet. Generate or select a world, then compare Naive, Rule-based, and AfterDue on Simulation."}
        </p>
      </section>

      <RevenueFunnel
        historicalUnpaid={historical}
        collectible={collectible}
        reviewRequired={review}
        excluded={excluded}
        cases={data.collectible_recovery_case_count ?? data.recovery_case_count}
        interventions={used}
        recovered={recovered}
      />

      <section className="grid gap-3 sm:grid-cols-3">
        <MetricCard
          label="Recovery cases"
          value={formatCount(data.collectible_recovery_case_count ?? data.recovery_case_count)}
        />
        <MetricCard
          label="Recovered revenue"
          value={recovered ? formatPaiseINR(recovered) : "—"}
          hint={
            afterDue
              ? "AfterDue on this run"
              : data.best_baseline_name
                ? strategyLabel(data.best_baseline_name)
                : "Run strategies on Simulation"
          }
        />
        <MetricCard
          label="Intervention budget"
          value={formatCount(data.intervention_budget)}
        />
        <MetricCard
          label="AfterDue vs best baseline"
          value={
            data.reclaim_vs_best_baseline_paise == null
              ? "—"
              : formatPaiseINR(data.reclaim_vs_best_baseline_paise)
          }
          hint="Incremental recovered revenue vs Naive/Rule-based"
        />
        <MetricCard
          label="Recovery yield"
          value={formatRatio(yieldValue)}
          hint="Recovered / collectible eligible revenue"
        />
      </section>

      {strategies.length === 0 ? (
        <EmptyState
          title="Baselines have not been run"
          body="Generate a world, then run Naive, Rule-based, and AfterDue on the same seed to compare recovery economics."
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
