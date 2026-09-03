import Link from "next/link";

export function EmptyState({
  title,
  body,
  href,
  action,
}: {
  title: string;
  body: string;
  href?: string;
  action?: string;
}) {
  return (
    <div className="rounded-md border border-dashed border-line bg-paper-raised px-6 py-10 text-center">
      <p className="text-sm font-medium text-ink">{title}</p>
      <p className="mx-auto mt-2 max-w-md text-sm leading-6 text-ink-soft">{body}</p>
      {href && action ? (
        <Link
          href={href}
          className="mt-5 inline-flex rounded-sm bg-forest px-3 py-2 text-xs font-medium uppercase tracking-[0.12em] text-paper-raised"
        >
          {action}
        </Link>
      ) : null}
    </div>
  );
}

export function ErrorState({ title, body }: { title: string; body: string }) {
  return (
    <div className="rounded-md border border-stop/30 bg-paper-raised px-6 py-8">
      <p className="text-sm font-medium text-stop">{title}</p>
      <p className="mt-2 text-sm text-ink-soft">{body}</p>
    </div>
  );
}

export function SkeletonGrid({ rows = 3 }: { rows?: number }) {
  return (
    <div className="grid gap-3 sm:grid-cols-3">
      {Array.from({ length: rows }).map((_, i) => (
        <div key={i} className="h-24 animate-pulse rounded-md bg-sand/70 motion-reduce:animate-none" />
      ))}
    </div>
  );
}
