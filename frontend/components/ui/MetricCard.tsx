export function MetricCard({
  label,
  value,
  hint,
  emphasize = false,
}: {
  label: string;
  value: string;
  hint?: string;
  emphasize?: boolean;
}) {
  return (
    <div
      className={`rounded-lg border px-4 py-4 ${
        emphasize
          ? "border-forest/30 bg-paper-raised shadow-[0_0_0_1px_rgba(43,107,237,0.08)]"
          : "border-line bg-paper-raised"
      }`}
    >
      <p className="text-[11px] font-medium uppercase tracking-[0.14em] text-ink-soft">
        {label}
      </p>
      <p className="mt-2 font-medium text-2xl tabular tracking-tight text-ink">{value}</p>
      {hint ? <p className="mt-1 text-xs leading-5 text-ink-soft">{hint}</p> : null}
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
      <h2 className="mt-2 text-3xl font-medium tracking-tight text-ink">{title}</h2>
      {body ? (
        <p className="mt-2 max-w-2xl text-sm leading-6 text-ink-soft">{body}</p>
      ) : null}
    </header>
  );
}
