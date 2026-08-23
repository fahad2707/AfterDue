export function SyntheticBadge({ compact = false }: { compact?: boolean }) {
  return (
    <span
      data-testid="synthetic-badge"
      className="inline-flex items-center rounded-sm border border-amber-soft bg-amber-soft px-2 py-0.5 text-[10px] font-medium uppercase tracking-[0.14em] text-amber"
    >
      {compact ? "Synthetic" : "Synthetic simulation"}
    </span>
  );
}
