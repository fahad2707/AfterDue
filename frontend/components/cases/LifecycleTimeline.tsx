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

  const steps = [
    { title: "Active", detail: createdAt ? `Subscription created ${formatDate(createdAt)}` : "Subscription was active", tone: "quiet" },
    { title: "Pending", detail: "Payment retries failed before halt", tone: "quiet" },
    { title: "Halted", detail: formatDate(caseRow.halted_at), tone: "warn" },
    {
      title: "Invoices accumulate",
      detail: `${caseRow.invoice_count} unpaid invoices during the halt episode`,
      tone: "warn",
    },
    { title: "Active", detail: `Returned ${formatDate(caseRow.reactivated_at)}`, tone: "good" },
    {
      title: "Recovery window opened",
      detail: episode?.episode_id
        ? `Case ${caseRow.case_id}`
        : "Recovery case created",
      tone: "good",
    },
  ];

  return (
    <ol className="grid gap-2 sm:grid-cols-2 xl:grid-cols-3">
      {steps.map((step, index) => (
        <li key={`${step.title}-${index}`} className="rounded-md border border-line bg-paper-raised px-3 py-3">
          <p className="font-mono text-[10px] text-ink-soft">{String(index + 1).padStart(2, "0")}</p>
          <p className="mt-1 text-sm font-medium">{step.title}</p>
          <p className="mt-1 text-xs leading-5 text-ink-soft">{step.detail}</p>
        </li>
      ))}
    </ol>
  );
}
