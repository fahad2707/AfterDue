import { PageHeader } from "@/components/ui/MetricCard";

export default function ArchitecturePage() {
  const steps = [
    ["Lifecycle", "Reconstruct ACTIVE → PENDING → HALTED → ACTIVE."],
    ["Historical unpaid", "Invoices issued during the halt episode remain."],
    ["Collectibility", "Invoice existence is not proof of a valid receivable."],
    ["Policy", "Deterministic rules decide which actions are allowed."],
    ["Recovery model", "Estimate P(recovery | action) on collectible debt only."],
    ["Economics", "Rank by expected incremental recovery under a budget."],
    ["Validator", "Re-check policy immediately before acting."],
    ["Simulated execution", "No real payment is attempted in this prototype."],
    ["Audit", "Every decision is recorded."],
  ] as const;

  return (
    <div className="space-y-8">
      <PageHeader
        eyebrow="Razorpay AI Buildathon · Track 03"
        title="Architecture"
        body="AfterDue is post-halt revenue intelligence. It is a synthetic prototype, not an official Razorpay product. Internal systems may still use the RECLAIM codename."
      />
      <ol className="space-y-3">
        {steps.map(([title, body], index) => (
          <li
            key={title}
            className="grid gap-2 rounded-md border border-line bg-paper-raised px-4 py-3 sm:grid-cols-[160px_minmax(0,1fr)]"
          >
            <p className="font-mono text-[11px] text-ink-soft">
              {String(index + 1).padStart(2, "0")} {title}
            </p>
            <p className="text-sm leading-6 text-ink">{body}</p>
          </li>
        ))}
      </ol>
    </div>
  );
}
