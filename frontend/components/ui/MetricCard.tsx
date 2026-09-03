type MetricTone = "neutral" | "good" | "attention" | "excluded" | "info";

const TONE: Record<MetricTone, string> = {
  neutral: "border-line bg-paper-raised",
  good: "border-good/25 bg-good-soft/60",
  attention: "border-attention/20 bg-amber-soft/50",
  excluded: "border-line bg-excluded-soft/80",
  info: "border-forest/25 bg-paper-raised",
};

export function MetricCard({
  label,
  value,
  hint,
  emphasize = false,
  tone = "neutral",
}: {
  label: string;
  value: string;
  hint?: string;
  emphasize?: boolean;
  tone?: MetricTone;
}) {
  return (
    <div className={`rounded-md border px-5 py-5 ${TONE[tone]}`}>
      <p
        className={`figure font-medium tracking-tight text-ink ${
          emphasize ? "text-3xl" : "text-2xl"
        }`}
      >
        {value}
      </p>
      <p className="mt-2 text-[11px] font-medium uppercase tracking-[0.14em] text-ink-soft">
        {label}
      </p>
      {hint ? <p className="mt-1.5 text-xs leading-5 text-ink-soft">{hint}</p> : null}
    </div>
  );
}

export function PageHeader({
  eyebrow,
  title,
  body,
}: {
  eyebrow: string;
  title: string;
  body?: string;
}) {
  return (
    <header>
      <p className="text-[11px] font-medium uppercase tracking-[0.16em] text-ink-soft">
        {eyebrow}
      </p>
      <h2 className="mt-2.5 text-3xl font-medium tracking-tight text-ink">{title}</h2>
      {body ? (
        <p className="mt-3 max-w-2xl text-sm leading-7 text-ink-soft">{body}</p>
      ) : null}
    </header>
  );
}
