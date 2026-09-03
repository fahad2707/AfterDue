import { PageHeader } from "@/components/ui/MetricCard";
import { ErrorState } from "@/components/ui/StateBlock";
import { formatRatio } from "@/lib/format/money";
import { apiGet } from "@/lib/server-api";
import type { ModelRun } from "@/types/api";

function asRecord(value: unknown): Record<string, unknown> {
  return value && typeof value === "object" ? (value as Record<string, unknown>) : {};
}

function num(value: unknown): string {
  return typeof value === "number" && Number.isFinite(value) ? value.toFixed(4) : "—";
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-md border border-line bg-paper-raised px-4 py-4">
      <p className="text-[11px] uppercase tracking-[0.12em] text-ink-soft">{label}</p>
      <p className="mt-2 font-mono text-lg tabular">{value}</p>
    </div>
  );
}

export default async function ModelPage() {
  const result = await apiGet<ModelRun>("/api/model/active");
  if (!result.ok) {
    return (
      <div className="space-y-6">
        <PageHeader
          eyebrow="Recovery model"
          title="Model"
        />
        <ErrorState
          title="No active model"
          body="Train a recovery model with POST /api/model/train. The LLM layer is not part of this path."
        />
      </div>
    );
  }

  const model = result.data;
  const metrics = asRecord(model.metrics);
  const validation = asRecord(asRecord(model.business_metrics).validation);
  const hash = model.feature_schema_hash.slice(0, 12);
  const confusion = Array.isArray(metrics.confusion) ? metrics.confusion : [];
  const bins = asRecord(metrics.calibration_bins);
  const meanPred = Array.isArray(bins.mean_predicted) ? bins.mean_predicted : [];
  const fracPos = Array.isArray(bins.fraction_positive) ? bins.fraction_positive : [];

  return (
    <div className="space-y-8">
      <PageHeader
        eyebrow="Business estimate, then diagnostics"
        title="Recovery model"
        body="The model estimates what is likely to happen with and without intervention on collectible debt. Diagnostics below measure calibration, not certainty. All results are synthetic."
      />

      <section className="rounded-lg border border-line bg-paper-raised px-4 py-5">
        <h3 className="text-[11px] uppercase tracking-[0.14em] text-ink-soft">
          Business estimate
        </h3>
        <dl className="mt-3 grid gap-4 sm:grid-cols-2">
          <div>
            <dt className="text-sm font-medium">Without intervention</dt>
            <dd className="mt-1 text-sm leading-6 text-ink-soft">
              Estimated recovery if AfterDue takes no action on a collectible
              case.
            </dd>
          </div>
          <div>
            <dt className="text-sm font-medium">With intervention</dt>
            <dd className="mt-1 text-sm leading-6 text-ink-soft">
              Estimated recovery under the selected allowed action.
            </dd>
          </div>
          <div>
            <dt className="text-sm font-medium">Intervention lift</dt>
            <dd className="mt-1 text-sm leading-6 text-ink-soft">
              Difference in estimated recovery probability versus no action.
            </dd>
          </div>
          <div>
            <dt className="text-sm font-medium">Expected incremental recovery</dt>
            <dd className="mt-1 text-sm leading-6 text-ink-soft">
              Collectible amount × lift, minus action cost. These are estimates,
              not guaranteed rupees.
            </dd>
          </div>
        </dl>
      </section>

      <section className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
        <Metric label="Active model" value={model.model_type.replaceAll("_", " ")} />
        <Metric label="Version" value={model.model_version} />
        <Metric label="Dataset seed" value={String(model.dataset_seed)} />
        <Metric label="Trained" value={model.trained_at.slice(0, 19)} />
        <Metric label="Schema hash" value={hash} />
        <Metric label="Examples" value={String(model.n_examples)} />
      </section>

      <p className="text-sm text-ink-soft">{model.selection_reason}</p>

      <section>
        <h3 className="mb-3 text-[11px] uppercase tracking-[0.14em] text-ink-soft">
          Model diagnostics · held-out classification
        </h3>
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          <Metric label="Precision" value={num(metrics.precision)} />
          <Metric label="Recall" value={num(metrics.recall)} />
          <Metric label="F1" value={num(metrics.f1)} />
          <Metric label="ROC-AUC" value={num(metrics.roc_auc)} />
          <Metric label="Brier score" value={num(metrics.brier)} />
          <Metric
            label="Calibrated"
            value={metrics.calibrated === true || model.calibrated ? "yes" : "no"}
          />
        </div>
      </section>

      {confusion.length === 2 ? (
        <section>
          <h3 className="mb-3 text-[11px] uppercase tracking-[0.14em] text-ink-soft">
            Confusion matrix
          </h3>
          <table className="text-sm">
            <thead>
              <tr className="text-[11px] uppercase tracking-[0.12em] text-ink-soft">
                <th className="py-2 pr-4 font-medium" />
                <th className="py-2 pr-4 font-medium">Pred 0</th>
                <th className="py-2 font-medium">Pred 1</th>
              </tr>
            </thead>
            <tbody className="font-mono">
              <tr>
                <td className="py-1.5 pr-4">Actual 0</td>
                <td className="py-1.5 pr-4">{String((confusion[0] as number[])[0])}</td>
                <td className="py-1.5">{String((confusion[0] as number[])[1])}</td>
              </tr>
              <tr>
                <td className="py-1.5 pr-4">Actual 1</td>
                <td className="py-1.5 pr-4">{String((confusion[1] as number[])[0])}</td>
                <td className="py-1.5">{String((confusion[1] as number[])[1])}</td>
              </tr>
            </tbody>
          </table>
        </section>
      ) : null}

      <section>
        <h3 className="mb-3 text-[11px] uppercase tracking-[0.14em] text-ink-soft">
          Calibration overview
        </h3>
        {meanPred.length === 0 ? (
          <p className="text-sm text-ink-soft">No calibration bins available.</p>
        ) : (
          <table className="w-full max-w-xl text-left text-sm">
            <thead>
              <tr className="border-b border-line text-[11px] uppercase tracking-[0.12em] text-ink-soft">
                <th className="py-2 font-medium">Mean predicted</th>
                <th className="py-2 font-medium">Observed positive rate</th>
              </tr>
            </thead>
            <tbody>
              {meanPred.map((pred, index) => (
                <tr key={`${pred}-${index}`} className="border-b border-line/70 font-mono">
                  <td className="py-1.5">{num(pred)}</td>
                  <td className="py-1.5">{num(fracPos[index])}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>

      {Object.keys(validation).length > 0 ? (
        <section>
          <h3 className="mb-3 text-[11px] uppercase tracking-[0.14em] text-ink-soft">
            Challenger comparison (validation Brier)
          </h3>
          <table className="w-full max-w-xl text-left text-sm">
            <thead>
              <tr className="border-b border-line text-[11px] uppercase tracking-[0.12em] text-ink-soft">
                <th className="py-2 font-medium">Model</th>
                <th className="py-2 font-medium">Brier</th>
                <th className="py-2 font-medium">ROC-AUC</th>
              </tr>
            </thead>
            <tbody>
              {Object.entries(validation).map(([name, raw]) => {
                const row = asRecord(raw);
                return (
                  <tr key={name} className="border-b border-line/70">
                    <td className="py-1.5 capitalize">{name.replaceAll("_", " ")}</td>
                    <td className="py-1.5 font-mono">{num(row.brier)}</td>
                    <td className="py-1.5 font-mono">{num(row.roc_auc)}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </section>
      ) : null}

      <p className="text-sm text-ink-soft">
        Accuracy is not the headline. Probabilities are multiplied by money, so
        Brier score and calibration matter. Strategy economics live on the
        simulation comparison, not on this page. Positive rate on the held-out
        set: {formatRatio(Number(asRecord(model.business_metrics).held_out_positive_rate))}
      </p>
    </div>
  );
}
