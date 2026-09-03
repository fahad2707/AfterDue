import { formatTime } from "@/lib/format/date";
import { formatPaiseINR } from "@/lib/format/money";
import type { AuditEntry } from "@/types/api";

function stageOf(eventType: string): string {
  if (eventType.includes("POLICY")) return "Policy";
  if (eventType.includes("MODEL")) return "Model";
  if (eventType.includes("VALIDAT") || eventType.includes("BLOCKED")) return "Validator";
  if (eventType.includes("EXECUTED") || eventType.includes("OUTCOME")) return "Execution";
  if (eventType.includes("AGENT") || eventType.includes("AUDIT") || eventType.includes("CASE_CLOSED")) {
    return "Audit";
  }
  if (eventType.includes("INVOICE") || eventType.includes("BACKLOG") || eventType.includes("COLLECT")) {
    return "Collectibility";
  }
  if (eventType.includes("STATE") || eventType.includes("HALT") || eventType.includes("REACTIV")) {
    return "Lifecycle";
  }
  return "Event";
}

function decisionOf(entry: AuditEntry): string {
  const details = entry.details;
  if (typeof details.to_status === "string") return String(details.to_status);
  if (typeof details.outcome === "string") return String(details.outcome);
  if (typeof details.action === "string") return String(details.action).replaceAll("_", " ");
  if (typeof details.stop_reason === "string") return String(details.stop_reason).replaceAll("_", " ");
  return entry.event_type.replaceAll("_", " ").toLowerCase();
}

function reasonOf(entry: AuditEntry): string | null {
  const details = entry.details;
  const parts: string[] = [];
  if (typeof details.from_status === "string" && typeof details.to_status === "string") {
    parts.push(`${details.from_status} → ${details.to_status}`);
  }
  if (typeof details.reason_code === "string") parts.push(details.reason_code.replaceAll("_", " "));
  if (typeof details.provenance === "string") parts.push(details.provenance.replaceAll("_", " "));
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
    <div className="overflow-x-auto rounded-md border border-line bg-paper-raised">
      <table className="w-full min-w-[720px] border-collapse text-left text-sm">
        <thead>
          <tr className="border-b border-line bg-sand/40 text-[11px] uppercase tracking-[0.1em] text-ink-soft">
            <th className="px-3 py-2.5 font-medium">Time</th>
            <th className="px-3 py-2.5 font-medium">Stage</th>
            <th className="px-3 py-2.5 font-medium">Decision</th>
            <th className="px-3 py-2.5 font-medium">Reason / provenance</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((entry) => (
            <tr key={entry.audit_id} className="border-b border-line/70 last:border-b-0">
              <td className="px-3 py-2.5 align-top font-mono text-[11px] whitespace-nowrap text-ink-soft">
                {formatTime(entry.ts)}
              </td>
              <td className="px-3 py-2.5 align-top text-[11px] uppercase tracking-[0.12em] text-ink-soft">
                {stageOf(entry.event_type)}
              </td>
              <td className="px-3 py-2.5 align-top">
                <p className="font-medium capitalize">{decisionOf(entry)}</p>
                <p className="mt-0.5 font-mono text-[11px] text-ink-soft">
                  {entry.event_type}
                </p>
              </td>
              <td className="px-3 py-2.5 align-top text-xs leading-5 text-ink-soft">
                {reasonOf(entry) ?? "—"}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
