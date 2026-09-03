"use client";

import { useState } from "react";

import { SyntheticBadge } from "@/components/console/SyntheticBadge";
import { ErrorState } from "@/components/ui/StateBlock";
import { runEvaluation } from "@/lib/api/evaluation";
import { formatCount, formatPaiseINR, formatRatio } from "@/lib/format/money";
import { strategyLabel } from "@/lib/format/policy";
import type { EvaluationReport, EvaluationStrategyRow } from "@/types/api";

const ORDER = ["naive", "rule_based", "reclaim", "oracle"];
const SIZES = [1000, 5000, 10000];

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

function rowsOf(report: EvaluationReport): EvaluationStrategyRow[] {
  return ORDER.map((key) => report.strategies[key]).filter(Boolean);
}

export function EvaluationConsole() {
  const [size, setSize] = useState(1000);
  const [seed, setSeed] = useState(42);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [report, setReport] = useState<EvaluationReport | null>(null);

  async function onRun() {
    setBusy(true);
    setError(null);
    try {
      const body = await runEvaluation({
        subscriber_count: size,
        seed,
        intervention_budget: null,
        bootstrap_samples: size >= 5000 ? 200 : 400,
        include_oracle: true,
      });
      setReport(body);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Evaluation failed.");
    } finally {
      setBusy(false);
    }
  }

  const reclaim = report?.strategies.reclaim;
  const naive = report?.strategies.naive;
  const invalidAvoided =
    reclaim && naive
      ? Math.max(0, naive.incorrectly_targeted_paise - reclaim.incorrectly_targeted_paise)
      : 0;

  return (
    <div className="space-y-8">
      <header className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <p className="font-mono text-[11px] uppercase tracking-[0.16em] text-ink-soft">
            Benchmark
          </p>
          <h2 className="mt-2 text-3xl font-medium tracking-tight">Evaluation</h2>
          <p className="mt-2 max-w-2xl text-sm leading-6 text-ink-soft">
            Compare Naive (ungated historical unpaid), Rule-based and AfterDue
            (collectibility-gated), and an expected-value oracle. Synthetic
            outcomes only.
          </p>
        </div>
        <SyntheticBadge />
      </header>

      <section className="rounded-md border border-line bg-paper-raised px-4 py-4">
        <div className="flex flex-wrap items-end gap-3">
          <label className="text-sm">
            <span className="block text-[11px] uppercase tracking-[0.12em] text-ink-soft">
              Subscribers
            </span>
            <select
              className="mt-1 border border-line bg-paper px-2 py-1.5 text-sm"
              value={size}
              onChange={(event) => setSize(Number(event.target.value))}
            >
              {SIZES.map((value) => (
                <option key={value} value={value}>
                  {value.toLocaleString("en-IN")}
                </option>
              ))}
            </select>
          </label>
          <label className="text-sm">
            <span className="block text-[11px] uppercase tracking-[0.12em] text-ink-soft">
              Seed
            </span>
            <input
              className="mt-1 w-24 border border-line bg-paper px-2 py-1.5 font-mono text-sm"
              type="number"
              value={seed}
              onChange={(event) => setSeed(Number.parseInt(event.target.value, 10) || 0)}
            />
          </label>
          <button
            type="button"
            disabled={busy}
            onClick={() => void onRun()}
            className="rounded-sm bg-ink px-3 py-2 text-[11px] font-medium uppercase tracking-[0.12em] text-paper-raised disabled:opacity-60"
          >
            {busy ? "Running benchmark…" : "Run benchmark"}
          </button>
        </div>
        <p className="mt-3 text-xs text-ink-soft">
          Budget scales at 25 slots per 100 subscribers (canonical ratio). 5,000+
          runs can take a minute. The world is not retuned so AfterDue wins.
        </p>
      </section>

      {error ? <ErrorState title="Evaluation failed" body={error} /> : null}

      {report ? (
        <>
          <section>
            <h3 className="mb-3 text-[11px] uppercase tracking-[0.14em] text-ink-soft">
              Benchmark summary
            </h3>
            <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-5">
              <Card
                label="Historical unpaid"
                value={formatPaiseINR(report.population.historical_unpaid_paise)}
              />
              <Card
                label="True collectible"
                value={formatPaiseINR(report.population.collectible_paise)}
              />
              <Card
                label="Net recovered"
                value={formatPaiseINR(reclaim?.net_recovered_paise ?? 0)}
                hint="AfterDue, after intervention cost"
              />
              <Card
                label="Incremental recovered"
                value={formatPaiseINR(reclaim?.incremental_recovered_paise ?? 0)}
                hint="Versus no intervention"
              />
              <Card
                label="Invalid debt avoided"
                value={formatPaiseINR(invalidAvoided)}
                hint="Naive targeted this; AfterDue did not"
              />
            </div>
          </section>

          <StrategyTable report={report} />
          <NetRecoveredBars report={report} />
          <CollectibilityImpact report={report} />
          <InterventionEfficiency report={report} />
          <Safety report={report} />
          <ScenarioBreakdown report={report} />
          <Diagnostics report={report} />
          <Limitations lines={report.limitations} />
        </>
      ) : null}
    </div>
  );
}

function StrategyTable({ report }: { report: EvaluationReport }) {
  const rows = rowsOf(report);
  return (
    <section>
      <h3 className="text-[11px] uppercase tracking-[0.14em] text-ink-soft">
        Strategy comparison
      </h3>
      <p className="mt-1 max-w-3xl text-sm text-ink-soft">
        Naive decides on ungated historical unpaid. Rule-based, AfterDue, and
        the oracle decide only after collectibility. Oracle is not deployable.
      </p>
      <div className="mt-4 overflow-x-auto rounded-md border border-line bg-paper-raised">
        <table className="w-full min-w-[860px] text-left text-sm">
          <thead>
            <tr className="border-b border-line text-[11px] uppercase tracking-[0.12em] text-ink-soft">
              <th className="px-3 py-2 font-medium">Strategy</th>
              <th className="px-3 py-2 font-medium">Universe</th>
              <th className="px-3 py-2 font-medium">Net recovered</th>
              <th className="px-3 py-2 font-medium">Incremental</th>
              <th className="px-3 py-2 font-medium">Invalid targeted</th>
              <th className="px-3 py-2 font-medium">Used</th>
              <th className="px-3 py-2 font-medium">Regret vs oracle</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr key={row.strategy_name} className="border-b border-line/70">
                <td className="px-3 py-2.5">{strategyLabel(row.strategy_name)}</td>
                <td className="px-3 py-2.5">{row.universe}</td>
                <td className="px-3 py-2.5 font-mono tabular">
                  {formatPaiseINR(row.net_recovered_paise)}
                </td>
                <td className="px-3 py-2.5 font-mono tabular">
                  {formatPaiseINR(row.incremental_recovered_paise)}
                </td>
                <td className="px-3 py-2.5 font-mono tabular">
                  {formatPaiseINR(row.incorrectly_targeted_paise)}
                </td>
                <td className="px-3 py-2.5 font-mono tabular">
                  {formatCount(row.interventions)}
                </td>
                <td className="px-3 py-2.5 font-mono tabular">
                  {row.regret_vs_oracle_paise == null
                    ? "—"
                    : formatPaiseINR(row.regret_vs_oracle_paise)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}

function NetRecoveredBars({ report }: { report: EvaluationReport }) {
  const rows = rowsOf(report);
  const max = Math.max(...rows.map((row) => row.net_recovered_paise), 1);
  return (
    <section>
      <h3 className="text-[11px] uppercase tracking-[0.14em] text-ink-soft">
        Recovery performance
      </h3>
      <p className="mt-1 text-sm text-ink-soft">Net recovered rupees (collectible minus cost).</p>
      <div className="mt-4 space-y-3">
        {rows.map((row) => (
          <div key={row.strategy_name}>
            <div className="mb-1 flex items-baseline justify-between gap-3">
              <span className="text-sm font-medium">{strategyLabel(row.strategy_name)}</span>
              <span className="font-mono text-sm tabular">
                {formatPaiseINR(row.net_recovered_paise)}
              </span>
            </div>
            <div className="h-2 rounded-sm bg-sand">
              <div
                className="h-2 rounded-sm bg-forest"
                style={{ width: `${Math.max(6, (row.net_recovered_paise / max) * 100)}%` }}
              />
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}

function CollectibilityImpact({ report }: { report: EvaluationReport }) {
  const pop = report.population;
  const naive = report.strategies.naive;
  const reclaim = report.strategies.reclaim;
  return (
    <section>
      <h3 className="text-[11px] uppercase tracking-[0.14em] text-ink-soft">
        Collectibility impact
      </h3>
      <p className="mt-1 max-w-3xl text-sm leading-6 text-ink-soft">
        Invoice existence is not proof of collectibility. A system that
        optimizes all historical unpaid can look busier while chasing excluded
        or review-required debt. Recovered rupees are still capped at true
        collectible value.
      </p>
      <div className="mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <Card label="Historical unpaid" value={formatPaiseINR(pop.historical_unpaid_paise)} />
        <Card label="Collectible" value={formatPaiseINR(pop.collectible_paise)} />
        <Card label="Excluded" value={formatPaiseINR(pop.not_collectible_paise)} />
        <Card label="Review required" value={formatPaiseINR(pop.review_required_paise)} />
      </div>
      <dl className="mt-4 grid gap-2 text-sm sm:grid-cols-2">
        <div>
          <dt className="text-ink-soft">Naive invalid / uncertain targeted</dt>
          <dd className="font-mono tabular">
            {formatPaiseINR(naive?.incorrectly_targeted_paise ?? 0)}
          </dd>
        </div>
        <div>
          <dt className="text-ink-soft">AfterDue invalid / uncertain targeted</dt>
          <dd className="font-mono tabular">
            {formatPaiseINR(reclaim?.incorrectly_targeted_paise ?? 0)}
          </dd>
        </div>
        <div>
          <dt className="text-ink-soft">Naive false collectibility rate</dt>
          <dd className="font-mono tabular">
            {formatRatio(naive?.false_collectibility_rate ?? 0)}
          </dd>
        </div>
        <div>
          <dt className="text-ink-soft">Human-review share of unpaid</dt>
          <dd className="font-mono tabular">{formatRatio(pop.human_review_rate)}</dd>
        </div>
      </dl>
    </section>
  );
}

function InterventionEfficiency({ report }: { report: EvaluationReport }) {
  const rows = rowsOf(report);
  return (
    <section>
      <h3 className="text-[11px] uppercase tracking-[0.14em] text-ink-soft">
        Intervention efficiency
      </h3>
      <div className="mt-4 overflow-x-auto rounded-md border border-line bg-paper-raised">
        <table className="w-full min-w-[640px] text-left text-sm">
          <thead>
            <tr className="border-b border-line text-[11px] uppercase tracking-[0.12em] text-ink-soft">
              <th className="px-3 py-2 font-medium">Strategy</th>
              <th className="px-3 py-2 font-medium">Interventions</th>
              <th className="px-3 py-2 font-medium">Unnecessary</th>
              <th className="px-3 py-2 font-medium">₹ / intervention</th>
              <th className="px-3 py-2 font-medium">Cost</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr key={row.strategy_name} className="border-b border-line/70">
                <td className="px-3 py-2.5">{strategyLabel(row.strategy_name)}</td>
                <td className="px-3 py-2.5 font-mono tabular">
                  {formatCount(row.interventions)}
                </td>
                <td className="px-3 py-2.5 font-mono tabular">
                  {formatCount(row.unnecessary_interventions)}
                </td>
                <td className="px-3 py-2.5 font-mono tabular">
                  {formatPaiseINR(row.recovery_per_intervention_paise)}
                </td>
                <td className="px-3 py-2.5 font-mono tabular">
                  {formatPaiseINR(row.intervention_cost_paise)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}

function Safety({ report }: { report: EvaluationReport }) {
  const rows = rowsOf(report);
  return (
    <section>
      <h3 className="text-[11px] uppercase tracking-[0.14em] text-ink-soft">Safety</h3>
      <div className="mt-4 overflow-x-auto rounded-md border border-line bg-paper-raised">
        <table className="w-full min-w-[640px] text-left text-sm">
          <thead>
            <tr className="border-b border-line text-[11px] uppercase tracking-[0.12em] text-ink-soft">
              <th className="px-3 py-2 font-medium">Strategy</th>
              <th className="px-3 py-2 font-medium">Violations attempted</th>
              <th className="px-3 py-2 font-medium">Violations executed</th>
              <th className="px-3 py-2 font-medium">Human escalations</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr key={row.strategy_name} className="border-b border-line/70">
                <td className="px-3 py-2.5">{strategyLabel(row.strategy_name)}</td>
                <td className="px-3 py-2.5 font-mono tabular">
                  {formatCount(row.policy_violations_attempted)}
                </td>
                <td className="px-3 py-2.5 font-mono tabular">
                  {formatCount(row.policy_violations_executed)}
                </td>
                <td className="px-3 py-2.5 font-mono tabular">
                  {formatCount(row.human_escalations)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}

function ScenarioBreakdown({ report }: { report: EvaluationReport }) {
  const families = Object.keys(report.family_labels);
  return (
    <section>
      <h3 className="text-[11px] uppercase tracking-[0.14em] text-ink-soft">
        Scenario breakdown
      </h3>
      <p className="mt-1 text-sm text-ink-soft">
        Families are labels on generated cases. A case may belong to more than one.
      </p>
      <div className="mt-4 overflow-x-auto rounded-md border border-line bg-paper-raised">
        <table className="w-full min-w-[720px] text-left text-sm">
          <thead>
            <tr className="border-b border-line text-[11px] uppercase tracking-[0.12em] text-ink-soft">
              <th className="px-3 py-2 font-medium">Family</th>
              {ORDER.filter((key) => report.strategies[key]).map((key) => (
                <th key={key} className="px-3 py-2 font-medium">
                  {strategyLabel(key)} incr.
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {families.map((family) => (
              <tr key={family} className="border-b border-line/70">
                <td className="px-3 py-2.5">{report.family_labels[family]}</td>
                {ORDER.filter((key) => report.strategies[key]).map((key) => (
                  <td key={key} className="px-3 py-2.5 font-mono tabular">
                    {formatPaiseINR(
                      report.scenario_breakdown[key]?.[family]?.incremental_paise ?? 0,
                    )}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}

function Diagnostics({ report }: { report: EvaluationReport }) {
  return (
    <section>
      <h3 className="text-[11px] uppercase tracking-[0.14em] text-ink-soft">
        Diagnostics
      </h3>
      <ul className="mt-3 max-w-3xl list-disc space-y-2 pl-5 text-sm leading-6 text-ink">
        {report.diagnostics.map((line) => (
          <li key={line}>{line}</li>
        ))}
      </ul>
      <p className="mt-3 text-xs text-ink-soft">
        Action agreement AfterDue vs Rule-based:{" "}
        {formatRatio(report.action_agreement.reclaim_vs_rule_based)}
        {report.intervals.reclaim?.incremental_recovered_paise
          ? ` · AfterDue incremental 95% bootstrap interval ${formatPaiseINR(
              report.intervals.reclaim.incremental_recovered_paise.low,
            )}–${formatPaiseINR(report.intervals.reclaim.incremental_recovered_paise.high)}`
          : null}
      </p>
    </section>
  );
}

function Limitations({ lines }: { lines: string[] }) {
  return (
    <section>
      <h3 className="text-[11px] uppercase tracking-[0.14em] text-ink-soft">
        Limitations
      </h3>
      <ul className="mt-3 max-w-3xl list-disc space-y-2 pl-5 text-sm leading-6 text-ink-soft">
        {lines.map((line) => (
          <li key={line}>{line}</li>
        ))}
      </ul>
    </section>
  );
}
