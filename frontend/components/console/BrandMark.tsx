type BrandSize = "sidebar" | "tour" | "hero";

const SIZES: Record<
  BrandSize,
  { mark: string; type: string; gap: string; tag: string }
> = {
  sidebar: {
    mark: "h-12 w-12",
    type: "text-[1.85rem]",
    gap: "gap-3.5",
    tag: "text-[10px]",
  },
  tour: {
    mark: "h-10 w-10",
    type: "text-[1.85rem]",
    gap: "gap-3.5",
    tag: "text-[11px]",
  },
  hero: {
    mark: "h-14 w-14 sm:h-16 sm:w-16",
    type: "text-[2.35rem] sm:text-6xl",
    gap: "gap-4",
    tag: "text-sm",
  },
};

function Mark({ className }: { className: string }) {
  return (
    <svg
      viewBox="0 0 40 40"
      className={`shrink-0 ${className}`}
      aria-hidden="true"
    >
      <rect width="40" height="40" rx="10" fill="#2a5fe8" />
      <path
        d="M13 9v22"
        stroke="#fff"
        strokeWidth="3.2"
        strokeLinecap="square"
      />
      <path
        d="M18 20h13"
        stroke="#fff"
        strokeWidth="3.2"
        strokeLinecap="round"
      />
      <path
        d="M27.5 14.5 34 20l-6.5 5.5"
        fill="none"
        stroke="#fff"
        strokeWidth="3.2"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

export function BrandMark({
  size = "sidebar",
  tagline = false,
}: {
  size?: BrandSize;
  tagline?: boolean;
}) {
  const scale = SIZES[size];
  return (
    <div className={`flex items-start ${scale.gap}`}>
      <Mark className={scale.mark} />
      <div className="min-w-0 pt-0.5">
        <p className={`wordmark whitespace-nowrap ${scale.type}`} aria-label="AfterDue">
          <span className="text-white/80">After</span>
          <span className="text-white">Due</span>
        </p>
        {tagline ? (
          <p
            className={`mt-2 font-medium uppercase tracking-[0.16em] text-white/50 ${scale.tag}`}
          >
            Post-halt revenue intelligence
          </p>
        ) : null}
      </div>
    </div>
  );
}
