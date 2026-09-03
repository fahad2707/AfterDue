"use client";

import { AnimatePresence, motion, useReducedMotion } from "framer-motion";
import { type ReactNode, useEffect } from "react";

import { BrandMark } from "@/components/console/BrandMark";
import { StatusBadge } from "@/components/ui/Badge";
import { TOUR_SCENE_COUNT } from "@/lib/tour";

export function TourChrome({
  scene,
  onNext,
  onPrev,
  onSkip,
  onFinish,
  children,
}: {
  scene: number;
  onNext: () => void;
  onPrev: () => void;
  onSkip: () => void;
  onFinish: () => void;
  children: ReactNode;
}) {
  const last = scene === TOUR_SCENE_COUNT - 1;
  const reduce = useReducedMotion();

  useEffect(() => {
    function onKey(event: KeyboardEvent) {
      if (event.key === "ArrowRight" || event.key === "Enter") {
        event.preventDefault();
        if (last) onFinish();
        else onNext();
      }
      if (event.key === "ArrowLeft") {
        event.preventDefault();
        onPrev();
      }
      if (event.key === "Escape") {
        event.preventDefault();
        onSkip();
      }
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [last, onFinish, onNext, onPrev, onSkip]);

  return (
    <div
      className="fixed inset-0 z-50 flex flex-col bg-forest-deep text-paper-raised"
      role="dialog"
      aria-modal="true"
      aria-labelledby="tour-title"
    >
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(ellipse_at_top,_var(--glow),_transparent_50%)]" />
      <div className="relative px-5 pb-2 pt-6 sm:px-10 sm:pt-8">
        {scene === 0 ? (
          <p className="text-[11px] font-medium uppercase tracking-[0.16em] text-white/40">
            Product tour
          </p>
        ) : (
          <BrandMark size="tour" />
        )}
      </div>
      <div className="relative flex min-h-0 flex-1 items-start justify-center px-5 pb-6 pt-8 sm:px-10 sm:pt-10">
        <AnimatePresence mode="wait">
          <motion.div
            key={scene}
            initial={reduce ? false : { opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={reduce ? { opacity: 1 } : { opacity: 0, y: -8 }}
            transition={{ duration: reduce ? 0 : 0.28 }}
            className="tour-motion w-full max-w-3xl"
          >
            {children}
          </motion.div>
        </AnimatePresence>
      </div>
      <div className="relative px-5 pb-16 pt-6 sm:px-10">
        <div className="flex items-center justify-between gap-3">
          <button
            type="button"
            onClick={onPrev}
            disabled={scene === 0}
            className="text-[11px] font-medium uppercase tracking-[0.14em] text-white/70 disabled:opacity-30"
          >
            Previous
          </button>
          <ol className="flex gap-1.5" aria-label="Tour progress">
            {Array.from({ length: TOUR_SCENE_COUNT }).map((_, index) => (
              <li
                key={index}
                className={`h-1.5 w-6 rounded-full ${
                  index === scene ? "bg-forest" : "bg-white/20"
                }`}
              />
            ))}
          </ol>
          <button
            type="button"
            onClick={last ? onFinish : onNext}
            className="rounded-sm bg-forest px-3 py-2 text-[11px] font-medium uppercase tracking-[0.12em] text-white"
          >
            {last ? "Enter AfterDue" : scene === 0 ? "Follow the leftover revenue" : "Next"}
          </button>
        </div>
        <button
          type="button"
          onClick={onSkip}
          className="absolute bottom-5 right-5 text-[11px] font-medium uppercase tracking-[0.14em] text-white/70 hover:text-white sm:right-10"
        >
          Skip intro
        </button>
      </div>
    </div>
  );
}

function FadeLines({
  lines,
  className = "text-2xl font-medium leading-snug tracking-tight sm:text-4xl",
}: {
  lines: string[];
  className?: string;
}) {
  const reduce = useReducedMotion();
  return (
    <div className="space-y-2">
      {lines.map((line, index) => (
        <motion.p
          key={line}
          className={className}
          initial={reduce ? false : { opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: reduce ? 0 : 0.08 * index, duration: 0.28 }}
        >
          {line}
        </motion.p>
      ))}
    </div>
  );
}

export function SceneIntro() {
  return (
    <div className="space-y-8">
      <div id="tour-title">
        <BrandMark size="hero" tagline />
      </div>
      <FadeLines
        lines={[
          "When an active subscription is halted,",
          "leftover invoices can still be issued.",
        ]}
      />
      <FadeLines
        className="text-lg leading-7 text-white/75 sm:text-xl"
        lines={[
          "When that customer returns to active,",
          "Razorpay does not charge those unpaid cycles automatically.",
        ]}
      />
      <p className="max-w-xl text-base leading-7 text-white/70">
        The merchant has to collect that leftover revenue — but only if it is
        actually collectible. AfterDue starts after the halt, not in the retry
        window.
      </p>
      <p className="text-xl font-medium text-white">
        How much of that leftover revenue is collectible?
      </p>
    </div>
  );
}

const STATES = ["Active", "Payment failed", "Pending", "Retries", "Halted"] as const;

export function SceneLifecycle() {
  const reduce = useReducedMotion();
  return (
    <div className="space-y-10">
      <p id="tour-title" className="text-[11px] font-medium uppercase tracking-[0.18em] text-white/55">
        Subscription lifecycle
      </p>
      <ol className="space-y-3">
        {STATES.map((label, index) => (
          <motion.li
            key={label}
            initial={reduce ? false : { opacity: 0, x: -8 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: reduce ? 0 : index * 0.08 }}
            className={`flex items-center gap-3 text-lg ${
              label === "Halted"
                ? "font-medium text-white"
                : "text-white/45"
            }`}
          >
            <span className="font-mono text-[11px] text-white/40">
              {String(index + 1).padStart(2, "0")}
            </span>
            {label}
          </motion.li>
        ))}
      </ol>
      <div className="space-y-3 border-t border-white/10 pt-8">
        <p className="text-sm uppercase tracking-[0.16em] text-white/45">Months later</p>
        <p className="text-2xl font-medium tracking-tight">Halted → Active</p>
        <p className="text-[11px] uppercase tracking-[0.16em] text-forest">AfterDue</p>
      </div>
      <p className="max-w-xl text-base leading-7 text-white/75">
        The customer returned. The historical unpaid invoices did not disappear.
        AfterDue begins on that HALTED → ACTIVE edge.
      </p>
    </div>
  );
}

export function SceneAssumption() {
  return (
    <div className="space-y-8">
      <p id="tour-title" className="text-[11px] uppercase tracking-[0.18em] text-white/55">
        The dangerous assumption
      </p>
      <p className="text-sm text-white/60">Illustrative seeded example · not a live case</p>
      <p className="figure text-5xl font-medium tracking-tight">₹31,996</p>
      <p className="text-[11px] uppercase tracking-[0.14em] text-white/50">
        Historical unpaid
      </p>
      <p className="text-lg text-white/55 line-through decoration-white/30">
        “₹31,996 available to recover.”
      </p>
      <p className="text-2xl font-medium">Not necessarily.</p>
      <p className="max-w-xl text-base leading-7 text-white/75">
        An unpaid invoice proves that an invoice exists. It does not prove the
        merchant delivered the service. Before asking how to recover it,
        AfterDue asks whether the money is collectible.
      </p>
    </div>
  );
}

const INVOICES = [
  { month: "Aug", amount: "₹7,999", service: "Unknown", result: "Review required", tone: "attention" as const },
  { month: "Sep", amount: "₹7,999", service: "Delivered", result: "Collectible", tone: "good" as const },
  { month: "Oct", amount: "₹7,999", service: "Suspended", result: "Excluded", tone: "excluded" as const },
  { month: "Nov", amount: "₹7,999", service: "Delivered", result: "Collectible", tone: "good" as const },
];

export function SceneCollectibility() {
  const reduce = useReducedMotion();
  return (
    <div className="space-y-8">
      <p id="tour-title" className="text-[11px] uppercase tracking-[0.18em] text-white/55">
        Collectibility
      </p>
      <p className="text-sm text-white/60">Illustrative seeded example · not a live case</p>
      <ul className="grid gap-2 sm:grid-cols-2">
        {INVOICES.map((row, index) => (
          <motion.li
            key={row.month}
            initial={reduce ? false : { opacity: 0, y: 6 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: reduce ? 0 : 0.1 * index }}
            className="rounded-md border border-white/10 bg-white/5 px-4 py-3"
          >
            <p className="figure text-xl font-medium">{row.amount}</p>
            <p className="mt-1 text-[11px] uppercase tracking-[0.12em] text-white/50">
              {row.month} · {row.service}
            </p>
            <div className="mt-2">
              <StatusBadge tone={row.tone}>{row.result}</StatusBadge>
            </div>
          </motion.li>
        ))}
      </ul>
      <dl className="grid grid-cols-2 gap-3 text-sm sm:grid-cols-4">
        <div>
          <dd className="figure font-medium">₹31,996</dd>
          <dt className="mt-1 text-white/50">Historical unpaid</dt>
        </div>
        <div>
          <dd className="figure font-medium">₹15,998</dd>
          <dt className="mt-1 text-white/50">Collectible</dt>
        </div>
        <div>
          <dd className="figure font-medium">₹7,999</dd>
          <dt className="mt-1 text-white/50">Excluded</dt>
        </div>
        <div>
          <dd className="figure font-medium">₹7,999</dd>
          <dt className="mt-1 text-white/50">Review required</dt>
        </div>
      </dl>
      <p className="text-lg font-medium">Only ₹15,998 enters recovery optimization.</p>
    </div>
  );
}

const PIPE = [
  ["Collectibility", "Is this receivable valid?"],
  ["Policy", "What are we allowed to do?"],
  ["Model", "What is likely under each permitted action?"],
  ["Economics", "Does acting create incremental value?"],
  ["Validator", "Is it still safe immediately before acting?"],
  ["Execution", "What happened?"],
  ["Audit", "Can we prove why?"],
] as const;

export function ScenePipeline() {
  const reduce = useReducedMotion();
  return (
    <div className="space-y-8">
      <p id="tour-title" className="text-[11px] uppercase tracking-[0.18em] text-white/55">
        Decision engine
      </p>
      <p className="text-2xl font-medium">Only now does optimization begin.</p>
      <p className="max-w-xl text-base leading-7 text-white/75">
        AfterDue separates whether money is owed from how it should be recovered.
      </p>
      <ol className="space-y-2">
        {PIPE.map(([title, body], index) => (
          <motion.li
            key={title}
            initial={reduce ? false : { opacity: 0, x: -8 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: reduce ? 0 : 0.07 * index }}
            className="grid grid-cols-[120px_minmax(0,1fr)] gap-3 border-l border-white/15 pl-3 text-sm sm:grid-cols-[140px_minmax(0,1fr)]"
          >
            <span className="font-medium">{title}</span>
            <span className="text-white/70">{body}</span>
          </motion.li>
        ))}
      </ol>
    </div>
  );
}

export function SceneDecision() {
  return (
    <div className="space-y-8">
      <p id="tour-title" className="text-[11px] uppercase tracking-[0.18em] text-white/55">
        The decision
      </p>
      <p className="text-sm text-white/60">
        Illustrative seeded example on ₹15,998 collectible · not live model output
      </p>
      <div className="grid gap-3 sm:grid-cols-2">
        <div className="rounded-md border border-white/10 bg-white/5 px-4 py-4">
          <p className="figure text-3xl font-medium">17.5%</p>
          <p className="mt-1.5 text-[11px] uppercase tracking-[0.14em] text-white/50">
            Without intervention
          </p>
          <p className="mt-1 text-sm text-white/70">P(recovery | no action)</p>
        </div>
        <div className="rounded-md border border-forest/40 bg-forest/15 px-4 py-4">
          <p className="figure text-3xl font-medium">50.4%</p>
          <p className="mt-1.5 text-[11px] uppercase tracking-[0.14em] text-white/50">
            With intervention
          </p>
          <p className="mt-1 text-sm text-white/70">P(recovery | action) · send payment link</p>
        </div>
      </div>
      <p className="text-xl font-medium">
        Estimated intervention lift{" "}
        <span className="figure">+32.9 pp</span>
      </p>
      <p>
        Expected incremental recovery{" "}
        <span className="figure font-medium">₹5,260</span>
      </p>
      <div className="flex flex-wrap gap-2">
        <StatusBadge tone="stop">Manual charge blocked</StatusBadge>
        <StatusBadge tone="good">Payment link allowed</StatusBadge>
        <StatusBadge tone="info">Recommend send payment link</StatusBadge>
      </div>
    </div>
  );
}

const GUARDS = [
  ["Customer opted out", "Stop"],
  ["Active dispute", "Stop / escalate"],
  ["Risk flag", "Escalate"],
  ["Contact cooldown", "Wait"],
  ["Max attempts", "Stop"],
  ["State changed", "Revalidate"],
] as const;

export function SceneBounds() {
  const reduce = useReducedMotion();
  return (
    <div className="space-y-8">
      <p id="tour-title" className="text-[11px] uppercase tracking-[0.18em] text-white/55">
        Bounded automation
      </p>
      <p className="text-2xl font-medium">
        Automation that touches money needs boundaries.
      </p>
      <ul className="space-y-2">
        {GUARDS.map(([rule, effect], index) => (
          <motion.li
            key={rule}
            initial={reduce ? false : { opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: reduce ? 0 : 0.06 * index }}
            className="flex items-center justify-between rounded-md border border-white/10 px-3 py-2 text-sm"
          >
            <span>{rule}</span>
            <span className="font-medium uppercase tracking-[0.12em] text-white/70">
              {effect}
            </span>
          </motion.li>
        ))}
      </ul>
      <p className="max-w-xl text-base leading-7 text-white/75">
        Every action is revalidated immediately before execution. Every decision
        leaves an audit trail. Execution in this prototype is simulated.
      </p>
    </div>
  );
}

export function SceneHandoff() {
  return (
    <div className="space-y-8">
      <p id="tour-title" className="sr-only">
        AfterDue
      </p>
      <p className="text-3xl font-medium tracking-tight">
        You&apos;ve seen the logic. Now inspect the system.
      </p>
      <p className="max-w-xl text-base leading-7 text-white/75">
        Overview, recovery cases, simulation, and evaluation all use the same
        synthetic laboratory. This is a Razorpay AI Buildathon prototype, not an
        official Razorpay product.
      </p>
      <p className="text-sm text-white/55">Replay later from the sidebar.</p>
    </div>
  );
}

export const TOUR_SCENES = [
  SceneIntro,
  SceneLifecycle,
  SceneAssumption,
  SceneCollectibility,
  ScenePipeline,
  SceneDecision,
  SceneBounds,
  SceneHandoff,
];
