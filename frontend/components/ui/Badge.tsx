export type StatusTone =
  | "neutral"
  | "good"
  | "stop"
  | "attention"
  | "info"
  | "excluded";

export function provenanceTone(
  provenance: string,
): "info" | "attention" | "stop" | "neutral" {
  if (provenance === "DOCUMENTED_PLATFORM_BEHAVIOR") return "info";
  if (provenance === "PRODUCT_DESIGN_ASSUMPTION") return "attention";
  if (provenance === "SAFETY_GUARDRAIL") return "stop";
  return "neutral";
}

export function collectibilityTone(status: string | undefined): StatusTone {
  if (status === "collectible") return "good";
  if (status === "not_collectible") return "excluded";
  if (status === "review_required") return "attention";
  return "neutral";
}

const STYLES: Record<StatusTone, string> = {
  neutral: "border-line bg-sand text-ink-soft",
  good: "border-good/20 bg-good-soft text-good",
  stop: "border-stop/25 bg-stop-soft text-stop",
  attention: "border-attention/20 bg-amber-soft text-attention",
  info: "border-forest/20 bg-forest/10 text-forest",
  excluded: "border-line bg-excluded-soft text-excluded",
};

const MARK: Record<StatusTone, string> = {
  neutral: "",
  good: "✓",
  stop: "×",
  attention: "!",
  info: "●",
  excluded: "–",
};

export function StatusBadge({
  tone = "neutral",
  children,
}: {
  tone?: StatusTone;
  children: string;
}) {
  const mark = MARK[tone];
  return (
    <span
      className={`inline-flex items-center gap-1 rounded-sm border px-1.5 py-0.5 text-[10px] font-medium uppercase tracking-[0.12em] ${STYLES[tone]}`}
    >
      {mark ? (
        <span aria-hidden="true" className="font-semibold">
          {mark}
        </span>
      ) : null}
      {children}
    </span>
  );
}
