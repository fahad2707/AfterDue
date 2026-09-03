"use client";

import { usePathname, useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";

import { RUN_QUERY, withRun } from "@/lib/run";
import {
  GUIDE_STEPS,
  markGuideSeen,
  type GuideStep,
} from "@/lib/guide";

type Box = { top: number; left: number; width: number; height: number };

function measure(id: string): Box | null {
  const node = document.querySelector(`[data-guide="${id}"]`);
  if (!(node instanceof HTMLElement)) return null;
  const rect = node.getBoundingClientRect();
  if (rect.width < 2 && rect.height < 2) return null;
  const pad = 6;
  return {
    top: Math.max(8, rect.top - pad),
    left: Math.max(8, rect.left - pad),
    width: rect.width + pad * 2,
    height: rect.height + pad * 2,
  };
}

export function UsageGuide({ onClose }: { onClose: () => void }) {
  const router = useRouter();
  const pathname = usePathname();
  const [index, setIndex] = useState(0);
  const [box, setBox] = useState<Box | null>(null);
  const step = GUIDE_STEPS[index];
  const last = index === GUIDE_STEPS.length - 1;

  const finish = useCallback(() => {
    markGuideSeen();
    onClose();
  }, [onClose]);

  const go = useCallback(
    (nextIndex: number) => {
      const next = GUIDE_STEPS[nextIndex];
      if (!next) {
        finish();
        return;
      }
      setIndex(nextIndex);
      const params = new URLSearchParams(window.location.search);
      const runId = params.get(RUN_QUERY);
      if (next.href !== pathname) {
        router.push(withRun(next.href, runId));
      }
    },
    [finish, pathname, router],
  );

  useEffect(() => {
    let cancelled = false;
    let attempts = 0;
    function sync() {
      if (cancelled) return;
      const found = measure(step.id);
      if (found) {
        setBox(found);
        return;
      }
      attempts += 1;
      if (attempts < 20) window.setTimeout(sync, 50);
    }
    sync();
    window.addEventListener("resize", sync);
    window.addEventListener("scroll", sync, true);
    return () => {
      cancelled = true;
      window.removeEventListener("resize", sync);
      window.removeEventListener("scroll", sync, true);
    };
  }, [step.id, pathname]);

  useEffect(() => {
    function onKey(event: KeyboardEvent) {
      if (event.key === "Escape") {
        event.preventDefault();
        finish();
      }
      if (event.key === "ArrowRight" || event.key === "Enter") {
        event.preventDefault();
        if (last) finish();
        else go(index + 1);
      }
      if (event.key === "ArrowLeft") {
        event.preventDefault();
        go(Math.max(0, index - 1));
      }
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [finish, go, index, last]);

  return (
    <div className="fixed inset-0 z-40" role="dialog" aria-modal="true" aria-labelledby="guide-title">
      <Spotlight box={box} />
      <Card
        step={step}
        index={index}
        last={last}
        box={box}
        onSkip={finish}
        onPrev={() => go(Math.max(0, index - 1))}
        onNext={() => (last ? finish() : go(index + 1))}
      />
    </div>
  );
}

function Spotlight({ box }: { box: Box | null }) {
  if (!box) {
    return <div className="absolute inset-0 bg-forest-deep/45" />;
  }
  const right = box.left + box.width;
  const bottom = box.top + box.height;
  return (
    <>
      <div className="absolute inset-x-0 top-0 bg-forest-deep/45" style={{ height: box.top }} />
      <div
        className="absolute left-0 bg-forest-deep/45"
        style={{ top: box.top, width: box.left, height: box.height }}
      />
      <div
        className="absolute bg-forest-deep/45"
        style={{ top: box.top, left: right, right: 0, height: box.height }}
      />
      <div className="absolute inset-x-0 bottom-0 bg-forest-deep/45" style={{ top: bottom }} />
      <div
        className="pointer-events-none absolute rounded-md ring-2 ring-forest shadow-[0_0_0_1px_rgba(43,107,237,0.35)]"
        style={{
          top: box.top,
          left: box.left,
          width: box.width,
          height: box.height,
        }}
      />
    </>
  );
}

function Card({
  step,
  index,
  last,
  box,
  onSkip,
  onPrev,
  onNext,
}: {
  step: GuideStep;
  index: number;
  last: boolean;
  box: Box | null;
  onSkip: () => void;
  onPrev: () => void;
  onNext: () => void;
}) {
  const style = tooltipStyle(box);
  return (
    <div
      className="absolute z-50 w-[min(22rem,calc(100vw-2rem))] rounded-lg border border-white/15 bg-paper-raised p-4 text-ink shadow-[0_12px_40px_rgba(8,20,39,0.28)]"
      style={style}
    >
      <p className="text-[10px] font-medium uppercase tracking-[0.16em] text-ink-soft">
        How to use AfterDue · {index + 1} of {GUIDE_STEPS.length}
      </p>
      <h2 id="guide-title" className="mt-2 text-base font-medium tracking-tight">
        {step.title}
      </h2>
      <p className="mt-2 text-sm leading-6 text-ink-soft">{step.body}</p>
      <div className="mt-4 flex items-center justify-between gap-2">
        <button
          type="button"
          onClick={onSkip}
          className="text-[11px] font-medium uppercase tracking-[0.12em] text-ink-soft hover:text-ink"
        >
          Skip guide
        </button>
        <div className="flex gap-2">
          <button
            type="button"
            onClick={onPrev}
            disabled={index === 0}
            className="rounded-md border border-line px-2.5 py-1.5 text-[11px] font-medium uppercase tracking-[0.12em] disabled:opacity-30"
          >
            Back
          </button>
          <button
            type="button"
            onClick={onNext}
            className="rounded-md bg-forest px-2.5 py-1.5 text-[11px] font-medium uppercase tracking-[0.12em] text-white"
          >
            {last ? "Done" : "Next"}
          </button>
        </div>
      </div>
    </div>
  );
}

function tooltipStyle(box: Box | null): { top: number; left: number } {
  if (!box) return { top: 96, left: 272 };
  const width = Math.min(352, typeof window === "undefined" ? 352 : window.innerWidth - 32);
  const left = Math.min(
    box.left + box.width + 16,
    (typeof window === "undefined" ? 1200 : window.innerWidth) - width - 16,
  );
  const top = Math.min(
    box.top,
    (typeof window === "undefined" ? 800 : window.innerHeight) - 220,
  );
  if (box.left < 280) {
    return { top: Math.max(16, top), left: Math.max(16, left) };
  }
  return { top: Math.max(16, box.top), left: Math.max(16, left) };
}
