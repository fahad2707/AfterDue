import { formatTime } from "@/lib/format/date";
import { formatPaiseINR } from "@/lib/format/money";
import type { AuditEntry } from "@/types/api";

function kind(eventType: string): "event" | "state" | "financial" | "policy" {
  if (eventType.includes("POLICY") || eventType.includes("RECOVERY_ESCALATED")) {
    return "policy";
  }
  if (
    eventType.includes("INVOICE") ||
    eventType.includes("BACKLOG") ||
    eventType.includes("RECOVERY")
  ) {
    return "financial";
  }
  if (eventType.includes("STATE") || eventType.includes("HALT")) {
    return "state";
  }
  return "event";
}

const KIND_LABEL = {
  event: "Event",
  state: "State",
  financial: "Financial",
  policy: "Policy",
};

function detailLine(entry: AuditEntry): string | null {
  const details = entry.details;
  const parts: string[] = [];
  if (typeof details.from_status === "string" && typeof details.to_status === "string") {
    parts.push(`${details.from_status} → ${details.to_status}`);
  }
  if (typeof details.event_type === "string") parts.push(details.event_type);
  if (typeof details.invoice_count === "number" && typeof details.backlog_amount_paise === "number") {
    parts.push(
      `${details.invoice_count} invoices · ${formatPaiseINR(details.backlog_amount_paise)}`,
    );
  }
  if (typeof details.halt_episode_id === "string") parts.push(details.halt_episode_id);
  return parts.length ? parts.join(" · ") : null;
}

export function AuditTimeline({ entries }: { entries: AuditEntry[] }) {
  const rows = [...entries].sort((a, b) => a.seq - b.seq);

  return (
    <ol className="space-y-3">
      {rows.map((entry) => {
        const tone = kind(entry.event_type);
        return (
          <li key={entry.audit_id} className="grid grid-cols-[72px_1fr] gap-3">
            <p className="font-mono text-[11px] text-ink-soft">{formatTime(entry.ts)}</p>
            <div className="border-l border-line pl-3">
              <p className="text-[10px] uppercase tracking-[0.14em] text-ink-soft">
                {KIND_LABEL[tone]}
              </p>
              <p className="mt-0.5 text-sm font-medium">
                {entry.event_type.replaceAll("_", " ")}
              </p>
              {detailLine(entry) ? (
                <p className="mt-1 font-mono text-xs text-ink-soft">{detailLine(entry)}</p>
              ) : null}
            </div>
          </li>
        );
      })}
    </ol>
  );
}
