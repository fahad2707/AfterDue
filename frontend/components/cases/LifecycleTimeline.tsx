import { formatDate } from "@/lib/format/date";
import type { HaltEpisode, RecoveryCase } from "@/types/api";

export function LifecycleTimeline({
  caseRow,
  createdAt,
  episodes,
}: {
  caseRow: RecoveryCase;
  createdAt: string | null;
  episodes: HaltEpisode[];
}) {
  const episode =
    episodes.find((item) => item.episode_id === caseRow.halt_episode_id) ??
    episodes[0];

  const quiet = [
    {
      title: "Active",
      detail: createdAt
        ? `Subscription created ${formatDate(createdAt)}`
        : "Subscription was active",
    },
    {
      title: "Pending / retries",
      detail: "Normal recovery lifecycle — failed payments before halt",
    },
  ];

  return (
    <div className="rounded-md border border-line bg-paper-raised px-4 py-4">
      <p className="text-[11px] uppercase tracking-[0.14em] text-ink-soft">
        Normal recovery lifecycle
      </p>
      <ol className="mt-3 grid gap-2 sm:grid-cols-2">
        {quiet.map((step) => (
          <li
            key={step.title}
            className="rounded-md border border-dashed border-line bg-surface-elevated px-3 py-3 opacity-70"
          >
            <p className="text-[11px] uppercase tracking-[0.12em] text-ink-soft">
              {step.title}
            </p>
            <p className="mt-1 text-xs leading-5 text-ink-soft">{step.detail}</p>
          </li>
        ))}
      </ol>

      <div className="mt-4 grid gap-2 border-t border-line pt-4 lg:grid-cols-[1fr_auto_1fr_auto_1fr] lg:items-stretch">
        <div className="rounded-md border border-attention/25 bg-amber-soft/40 px-3 py-3">
          <p className="text-[11px] uppercase tracking-[0.14em] text-attention">Halted</p>
          <p className="mt-1 figure text-sm font-medium">{formatDate(caseRow.halted_at)}</p>
          <p className="mt-1 text-xs leading-5 text-ink-soft">
            {caseRow.invoice_count} unpaid invoices accumulated during the halt episode
            {episode?.episode_id ? ` · ${episode.episode_id}` : ""}
          </p>
        </div>
        <p
          className="hidden items-center justify-center text-xs uppercase tracking-[0.16em] text-ink-soft lg:flex"
          aria-hidden="true"
        >
          →
        </p>
        <div className="rounded-md border border-forest/25 bg-forest/5 px-3 py-3">
          <p className="text-[11px] uppercase tracking-[0.14em] text-forest">Active</p>
          <p className="mt-1 figure text-sm font-medium">
            {formatDate(caseRow.reactivated_at)}
          </p>
          <p className="mt-1 text-xs leading-5 text-ink-soft">
            Customer returned. Previous unpaid cycles are not auto-charged.
          </p>
        </div>
        <p
          className="hidden items-center justify-center text-xs uppercase tracking-[0.16em] text-ink-soft lg:flex"
          aria-hidden="true"
        >
          →
        </p>
        <div className="rounded-md border border-forest/40 bg-navy-mid px-3 py-3 text-paper-raised">
          <p className="text-[11px] uppercase tracking-[0.14em] text-white/70">
            Post-halt
          </p>
          <p className="mt-1 text-sm font-medium tracking-tight">AfterDue</p>
          <p className="mt-1 text-xs leading-5 text-white/70">
            Recovery window opened for leftover revenue.
          </p>
        </div>
      </div>
    </div>
  );
}
