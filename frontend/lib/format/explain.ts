import { formatPaiseINR } from "@/lib/format/money";
import { actionLabel } from "@/lib/format/policy";

const REASON_SENTENCES: Record<string, string> = {
  DOMESTIC_CARD_MANUAL_CHARGE_UNSUPPORTED:
    "Direct manual charging is blocked because this subscription uses a domestic card. A customer-authorized payment journey remains permitted.",
  MANDATE_CAP_EXCEEDED:
    "Manual charging is blocked because the unpaid backlog exceeds the mandate cap used by this prototype.",
  RISK_FLAG_PRESENT:
    "Automated collection is blocked because a risk flag is present. The case requires merchant escalation.",
  ACTIVE_DISPUTE:
    "Automated recovery is stopped because this customer has an active dispute.",
  CUSTOMER_OPTED_OUT:
    "Payment-link contact is blocked because the customer has opted out.",
  MAX_ATTEMPTS_REACHED:
    "Automated collection is blocked because the attempt limit has been reached.",
  CONTACT_COOLDOWN_ACTIVE:
    "A further payment-link contact is blocked while the contact cooldown is active.",
};

export function explainCase(input: {
  invoiceCount: number;
  backlogPaise: number;
  reasonCodes: string[];
  allowedActions: string[];
}): string[] {
  const opening = `RECLAIM opened this recovery case because the subscription returned to ACTIVE after a halted period, and collectibility validation found ${input.invoiceCount} eligible invoice${input.invoiceCount === 1 ? "" : "s"} totaling ${formatPaiseINR(input.backlogPaise)}.`;
  const reasons = input.reasonCodes
    .map((code) => REASON_SENTENCES[code])
    .filter((line): line is string => Boolean(line));
  const unique = [...new Set(reasons)];
  if (unique.length === 0 && input.allowedActions.length) {
    unique.push(
      `Permitted actions right now: ${input.allowedActions.map(actionLabel).join(", ")}. No recovery action is executed in this console.`,
    );
  }
  return [opening, ...unique];
}
