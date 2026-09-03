"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import { StrategyComparison } from "@/components/dashboard/StrategyComparison";
import { SyntheticBadge } from "@/components/console/SyntheticBadge";
import { EmptyState, ErrorState } from "@/components/ui/StateBlock";
import { generateWorld, runBaselines } from "@/lib/api/simulation";
import { DEMO_CONFIG } from "@/lib/demo";
import { formatCount, formatPaiseINR } from "@/lib/format/money";
import { withRun } from "@/lib/run";
import type { SimulationConfig, StrategyMetrics, WorldSummary } from "@/types/api";

type Field = {
  key: keyof SimulationConfig;
  label: string;
  step?: number;
};

const FIELDS: Field[] = [
  { key: "subscriber_count", label: "Subscriber count" },
  { key: "seed", label: "Seed" },
  { key: "intervention_budget", label: "Intervention budget" },
  { key: "halt_rate", label: "Halt rate", step: 0.01 },
  { key: "reactivation_rate", label: "Reactivation rate", step: 0.01 },
  { key: "domestic_card_ratio", label: "Domestic card ratio", step: 0.01 },
  { key: "min_missed_cycles", label: "Min missed cycles" },
  { key: "max_missed_cycles", label: "Max missed cycles" },
  { key: "plan_amount_min_paise", label: "Plan min (paise)" },
  { key: "plan_amount_max_paise", label: "Plan max (paise)" },
  { key: "risk_flag_rate", label: "Risk flag rate", step: 0.01 },
  { key: "dispute_rate", label: "Dispute rate", step: 0.01 },
  { key: "opt_out_rate", label: "Opt-out rate", step: 0.01 },
];

export function SimulateConsole({ initialRunId }: { initialRunId: string | null }) {
  const router = useRouter();
  const [config, setConfig] = useState<SimulationConfig>({ ...DEMO_CONFIG });
  const [busy, setBusy] = useState<"generate" | "run" | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [runId, setRunId] = useState<string | null>(initialRunId);
  const [world, setWorld] = useState<WorldSummary | null>(null);
  const [results, setResults] = useState<Record<string, StrategyMetrics> | null>(null);

  function update(key: keyof SimulationConfig, raw: string) {
    const value = raw.includes(".") ? Number.parseFloat(raw) : Number.parseInt(raw, 10);
    setConfig((current) => ({ ...current, [key]: Number.isNaN(value) ? 0 : value }));
  }

  async function onGenerate() {
    setBusy("generate");
    setError(null);
    setResults(null);
    try {
      const created = await generateWorld(config);
      setRunId(created.run_id);
      setWorld(created.world_summary);
      router.replace(withRun("/simulate", created.run_id));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Simulation generation failed.");
    } finally {
      setBusy(null);
    }
  }

  async function onRun() {
    if (!runId) return;
    setBusy("run");
    setError(null);
    try {
      const executed = await runBaselines(runId);
      setResults(executed.strategy_results);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Strategy run failed.");
    } finally {
      setBusy(null);
    }
  }

  function replaySeed() {
    setConfig((current) => ({ ...current, seed: DEMO_CONFIG.seed }));
  }

  return (
    <div className="space-y-8">
      <header>
        <p className="text-[11px] font-medium uppercase tracking-[0.16em] text-ink-soft">
          Simulated execution
        </p>
        <h2 className="mt-2.5 text-3xl font-medium tracking-tight">Simulation</h2>
        <div className="mt-3 flex flex-wrap items-center gap-3">
          <SyntheticBadge />
          <p className="text-sm text-ink-soft">
            This is simulated execution, not production money movement. Results
            are illustrative and are not Razorpay production statistics.
          </p>
        </div>
      </header>

      <form
        className="rounded-md border border-line bg-paper-raised p-5"
        onSubmit={(event) => {
          event.preventDefault();
          void onGenerate();
        }}
      >
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {FIELDS.map((field) => (
            <label key={field.key} className="block">
              <span className="text-[11px] uppercase tracking-[0.12em] text-ink-soft">
                {field.label}
              </span>
              <input
                className="mt-1 w-full rounded-sm border border-line bg-paper px-2 py-1.5 font-mono text-sm outline-none focus:border-forest"
                type="number"
                step={field.step ?? 1}
                value={config[field.key] ?? ""}
                onChange={(event) => update(field.key, event.target.value)}
              />
            </label>
          ))}
        </div>
        <div className="mt-5 flex flex-wrap items-center gap-3">
          <button
            type="submit"
            disabled={busy !== null}
            className="rounded-sm bg-forest px-3 py-2 text-[11px] font-medium uppercase tracking-[0.12em] text-paper-raised disabled:opacity-60"
          >
            {busy === "generate" ? "Generating world…" : "Generate synthetic world"}
          </button>
          <button
            type="button"
            onClick={replaySeed}
            className="rounded-sm border border-line px-3 py-2 text-[11px] font-medium uppercase tracking-[0.12em]"
          >
            Replay same seed
          </button>
          <p className="font-mono text-xs text-ink-soft">Seed: {config.seed}</p>
        </div>
      </form>

      {error ? <ErrorState title="Simulation could not finish" body={error} /> : null}

      {world && runId ? (
        <section className="rounded-md border border-line bg-paper-raised p-5">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <p className="text-[11px] uppercase tracking-[0.12em] text-ink-soft">
                Generated run
              </p>
              <p className="mt-1 font-mono text-sm">{runId}</p>
            </div>
            <button
              type="button"
              disabled={busy !== null}
              onClick={() => void onRun()}
              className="rounded-sm bg-ink px-3 py-2 text-[11px] font-medium uppercase tracking-[0.12em] text-paper-raised disabled:opacity-60"
            >
              {busy === "run" ? "Running strategies…" : "Run Naive / Rule-based / AfterDue"}
            </button>
          </div>
          <dl className="mt-4 grid gap-3 sm:grid-cols-3">
            <div>
              <dd className="figure text-lg font-medium">
                {formatCount(
                  world.collectible_recovery_case_count ?? world.recovery_case_count,
                )}
              </dd>
              <dt className="mt-1 text-xs text-ink-soft">Collectible cases</dt>
            </div>
            <div>
              <dd className="figure text-lg font-medium">
                {formatPaiseINR(
                  world.collectible_amount_paise ?? world.revenue_at_risk_paise,
                )}
              </dd>
              <dt className="mt-1 text-xs text-ink-soft">Collectible receivables</dt>
            </div>
            <div>
              <dd className="figure text-lg font-medium">
                {formatPaiseINR(
                  world.historical_unpaid_amount_paise ?? world.revenue_at_risk_paise,
                )}
              </dd>
              <dt className="mt-1 text-xs text-ink-soft">Historical unpaid</dt>
            </div>
          </dl>
          <p className="mt-4 text-xs text-ink-soft">
            Simulated execution only. No real payment is attempted.
          </p>
        </section>
      ) : (
        <EmptyState
          title="No world on this page yet"
          body="Use the canonical demo values (100 subscribers, seed 42, budget 25) or change the knobs, then generate."
        />
      )}

      {results ? <StrategyComparison results={results} /> : null}
    </div>
  );
}
