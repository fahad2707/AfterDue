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
  return (
    <section>
      <h3 className="text-[11px] font-medium uppercase tracking-[0.14em] text-ink-soft">
        How leftover revenue is treated
      </h3>
      <p className="mt-2 max-w-2xl text-sm leading-6 text-ink-soft">
        Historical unpaid is reconstructed first. Collectibility then splits the
        total: recoverable opportunity, merchant review, and excluded non-receivables.
      </p>

      <div className="mt-4 grid gap-3 lg:grid-cols-[minmax(0,1.2fr)_minmax(0,0.8fr)]">
        <ol className="space-y-2">
          <li className="rounded-md border border-line bg-paper-raised px-4 py-4">
            <p className="figure text-2xl font-medium tracking-tight">
              {formatPaiseINR(historicalUnpaid)}
            </p>
            <p className="mt-1 text-[11px] uppercase tracking-[0.14em] text-ink-soft">
              Historical unpaid
            </p>
            <p className="mt-1 text-xs text-ink-soft">Invoice lineage after halt</p>
          </li>
          <li className="rounded-md border border-good/25 bg-good-soft/70 px-4 py-4">
            <p className="figure text-2xl font-medium tracking-tight text-good">
              {formatPaiseINR(collectible)}
            </p>
            <p className="mt-1 text-[11px] uppercase tracking-[0.14em] text-ink-soft">
              Collectible
            </p>
            <p className="mt-1 text-xs text-ink-soft">
              {formatCount(cases)} collectible cases · {formatCount(interventions)} selected
            </p>
          </li>
          <li className="rounded-md border border-forest/25 bg-paper-raised px-4 py-4">
            <p className="figure text-2xl font-medium tracking-tight">
              {formatPaiseINR(recovered)}
            </p>
            <p className="mt-1 text-[11px] uppercase tracking-[0.14em] text-ink-soft">
              Recovered
            </p>
            <p className="mt-1 text-xs text-ink-soft">Simulated, collectible only</p>
          </li>
        </ol>
        <div className="space-y-2">
          <p className="text-[11px] uppercase tracking-[0.14em] text-ink-soft">
            Leaves the funnel
          </p>
          <div className="rounded-md border border-attention/20 bg-amber-soft/50 px-4 py-4">
            <p className="figure text-xl font-medium">{formatPaiseINR(reviewRequired)}</p>
            <p className="mt-1 text-[11px] uppercase tracking-[0.12em] text-ink-soft">
              Review required
            </p>
            <p className="mt-1 text-xs text-ink-soft">Not collectible yet</p>
          </div>
          <div className="rounded-md border border-line bg-excluded-soft px-4 py-4">
            <p className="figure text-xl font-medium text-excluded">
              {formatPaiseINR(excluded)}
            </p>
            <p className="mt-1 text-[11px] uppercase tracking-[0.12em] text-ink-soft">
              Excluded
            </p>
            <p className="mt-1 text-xs text-ink-soft">Not a valid receivable</p>
          </div>
        </div>
      </div>
    </section>
  );
}
