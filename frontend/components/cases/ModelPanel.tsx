import { formatLiftPp, formatPaiseINR, formatRatio } from "@/lib/format/money";
import { actionLabel } from "@/lib/format/policy";
import type { ModelAnalysis } from "@/types/api";

export function ModelPanel({ analysis }: { analysis: ModelAnalysis | null | undefined }) {
  if (!analysis) {
    return (
      <section data-testid="recovery-model-panel">
        <h3 className="mb-3 text-[11px] uppercase tracking-[0.14em] text-ink-soft">
          What the model estimates
        </h3>
        <p className="text-sm text-ink-soft">
          No active recovery model. Train one on the Model page. These figures
          are model estimates from the synthetic environment, not guaranteed
          recovery.
        </p>
      </section>
    );
  }

  return (
    <section data-testid="recovery-model-panel">
      <h3 className="mb-3 text-[11px] uppercase tracking-[0.14em] text-ink-soft">
        What the model estimates
      </h3>
      <p className="mb-4 max-w-2xl text-sm text-ink-soft">
        The useful number is the difference between outcomes, not the probability
        itself. Expected incremental recovery subtracts action cost. These are
        synthetic estimates, not guaranteed recovery.
      </p>

      <div className="grid gap-3 lg:grid-cols-[1fr_auto_1fr]">
        <div className="rounded-md border border-line bg-paper-raised px-4 py-4">
          <p className="figure text-3xl font-medium tracking-tight">
            {formatRatio(analysis.p_no_action)}
          </p>
          <p className="mt-1.5 text-[11px] uppercase tracking-[0.14em] text-ink-soft">
            Without intervention
          </p>
          <p className="mt-1 text-xs text-ink-soft">P(recovery | no action)</p>
          <p className="mt-2 figure text-sm text-ink-soft">
            {formatPaiseINR(analysis.estimated_recovery_no_action_paise)}
          </p>
        </div>
        <p
          className="hidden items-center justify-center text-xs uppercase tracking-[0.16em] text-ink-soft lg:flex"
          aria-hidden="true"
        >
          →
        </p>
        <div className="rounded-md border border-forest/25 bg-paper-raised px-4 py-4">
          <p className="figure text-3xl font-medium tracking-tight">
            {formatRatio(analysis.p_selected_action)}
          </p>
          <p className="mt-1.5 text-[11px] uppercase tracking-[0.14em] text-ink-soft">
            With intervention
          </p>
          <p className="mt-1 text-xs text-ink-soft">P(recovery | action)</p>
          <p className="mt-2 text-sm capitalize text-ink-soft">
            {actionLabel(analysis.selected_action)}
            <span className="ml-2 figure">{formatPaiseINR(analysis.estimated_recovery_selected_paise)}</span>
          </p>
        </div>
      </div>

      <div className="mt-3 grid gap-3 sm:grid-cols-2">
        <div className="rounded-md border border-forest/30 bg-forest/5 px-4 py-4">
          <p className="figure text-3xl font-medium tracking-tight text-forest">
            {formatLiftPp(analysis.estimated_uplift)}
          </p>
          <p className="mt-1.5 text-[11px] uppercase tracking-[0.14em] text-ink-soft">
            Estimated intervention lift
          </p>
        </div>
        <div className="rounded-md border border-good/25 bg-good-soft/70 px-4 py-4">
          <p className="figure text-3xl font-medium tracking-tight text-good">
            {formatPaiseINR(analysis.expected_incremental_recovery_paise)}
          </p>
          <p className="mt-1.5 text-[11px] uppercase tracking-[0.14em] text-ink-soft">
            Expected incremental recovery
          </p>
        </div>
      </div>
      <p className="mt-3 font-mono text-[11px] text-ink-soft">
        Model {analysis.model_version} · {analysis.model_type}
      </p>
    </section>
  );
}
