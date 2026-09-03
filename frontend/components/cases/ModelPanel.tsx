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
        Model-estimated recovery and estimated intervention lift. Expected
        incremental recovery subtracts action cost. These are synthetic
        estimates, not guaranteed recovery.
      </p>
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <div className="rounded-md border border-line bg-paper-raised px-4 py-4">
          <p className="text-[11px] uppercase tracking-[0.12em] text-ink-soft">
            Without intervention
          </p>
          <p className="mt-2 font-mono text-xl tabular">
            {formatPaiseINR(analysis.estimated_recovery_no_action_paise)}
          </p>
          <p className="mt-1 font-mono text-xs text-ink-soft">
            {formatRatio(analysis.p_no_action)} model-estimated recovery
          </p>
        </div>
        <div className="rounded-md border border-line bg-paper-raised px-4 py-4">
          <p className="text-[11px] uppercase tracking-[0.12em] text-ink-soft">
            With recommended action
          </p>
          <p className="mt-2 font-mono text-xl tabular">
            {formatPaiseINR(analysis.estimated_recovery_selected_paise)}
          </p>
          <p className="mt-1 text-xs capitalize text-ink-soft">
            {actionLabel(analysis.selected_action)}
          </p>
        </div>
        <div className="rounded-md border border-line bg-paper-raised px-4 py-4">
          <p className="text-[11px] uppercase tracking-[0.12em] text-ink-soft">
            Estimated intervention lift
          </p>
          <p className="mt-2 font-mono text-xl tabular">
            {formatLiftPp(analysis.estimated_uplift)}
          </p>
        </div>
        <div className="rounded-md border border-line bg-paper-raised px-4 py-4">
          <p className="text-[11px] uppercase tracking-[0.12em] text-ink-soft">
            Expected incremental recovery
          </p>
          <p className="mt-2 font-mono text-xl tabular">
            {formatPaiseINR(analysis.expected_incremental_recovery_paise)}
          </p>
        </div>
      </div>
      <p className="mt-3 font-mono text-[11px] text-ink-soft">
        Model {analysis.model_version} · {analysis.model_type}
      </p>
    </section>
  );
}
