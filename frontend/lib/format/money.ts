const PAISE_PER_RUPEE = 100;

function groupIndian(rupees: number): string {
  const digits = String(Math.abs(rupees));
  if (digits.length <= 3) return digits;
  const head = digits.slice(0, -3);
  const tail = digits.slice(-3);
  const pairs: string[] = [];
  let rest = head;
  while (rest.length > 2) {
    pairs.unshift(rest.slice(-2));
    rest = rest.slice(0, -2);
  }
  if (rest) pairs.unshift(rest);
  return [...pairs, tail].join(",");
}

/** Format integer paise as INR rupees. 1499700 → ₹14,997 */
export function formatPaiseINR(amountPaise: number): string {
  if (!Number.isInteger(amountPaise)) {
    throw new TypeError("amount must be integer paise");
  }
  const sign = amountPaise < 0 ? "-" : "";
  const rupees = Math.trunc(Math.abs(amountPaise) / PAISE_PER_RUPEE);
  return `${sign}₹${groupIndian(rupees)}`;
}

export function formatRatio(value: number | null | undefined): string {
  if (value == null || Number.isNaN(value)) return "—";
  return `${(value * 100).toFixed(1)}%`;
}

export function formatCount(value: number | null | undefined): string {
  if (value == null) return "—";
  return new Intl.NumberFormat("en-IN").format(value);
}

/** Probability difference as percentage points. 0.36 → +36.0 pp */
export function formatLiftPp(uplift: number | null | undefined): string {
  if (uplift == null || Number.isNaN(uplift)) return "—";
  const points = uplift * 100;
  const sign = points > 0 ? "+" : "";
  return `${sign}${points.toFixed(1)} pp`;
}
