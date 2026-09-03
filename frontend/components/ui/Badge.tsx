export function provenanceTone(
  provenance: string,
): "info" | "attention" | "stop" | "neutral" {
  if (provenance === "DOCUMENTED_PLATFORM_BEHAVIOR") return "info";
  if (provenance === "PRODUCT_DESIGN_ASSUMPTION") return "attention";
  if (provenance === "SAFETY_GUARDRAIL") return "stop";
  return "neutral";
}

export function collectibilityTone(
  status: string | undefined,
): "good" | "stop" | "attention" | "neutral" {
  if (status === "collectible") return "good";
  if (status === "not_collectible") return "stop";
  if (status === "review_required") return "attention";
  return "neutral";
}

export function StatusBadge({
  tone = "neutral",
  children,
}: {
  tone?: "neutral" | "good" | "stop" | "attention" | "info";
  children: string;
}) {
  const styles = {
    neutral: "border-line bg-sand text-ink-soft",
    good: "border-good/20 bg-good/10 text-good",
    stop: "border-stop/20 bg-stop/10 text-stop",
    attention: "border-attention/20 bg-amber-soft text-attention",
    info: "border-forest/20 bg-forest/10 text-forest",
  }[tone];
  return (
    <span
      className={`inline-flex items-center rounded-md border px-2 py-0.5 text-[10px] font-medium uppercase tracking-[0.12em] ${styles}`}
    >
      {children}
    </span>
  );
}
