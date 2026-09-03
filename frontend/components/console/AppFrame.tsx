"use client";

import Link from "next/link";
import { usePathname, useSearchParams } from "next/navigation";
import { type ReactNode, useState, useSyncExternalStore } from "react";

import { PRIMARY_NAV } from "@/components/console/NavLinks";
import { ProductTour } from "@/components/tour/ProductTour";
import { UsageGuide } from "@/components/tour/UsageGuide";
import {
  GUIDE_QUERY,
  clearGuideSeen,
  guideSeen,
  subscribeGuide,
} from "@/lib/guide";
import { RUN_QUERY, withRun } from "@/lib/run";
import {
  TOUR_QUERY,
  clearTourSeen,
  subscribeTour,
  tourSeen,
} from "@/lib/tour";

function subscribeMount() {
  return () => {};
}

function guideId(href: string): string {
  return href === "/" ? "nav-overview" : `nav-${href.replace(/^\//, "")}`;
}

export function AppFrame({
  sidebarFooter,
  children,
}: {
  sidebarFooter: ReactNode;
  children: ReactNode;
}) {
  const pathname = usePathname();
  const params = useSearchParams();
  const runId = params.get(RUN_QUERY);
  const forceTour = params.get(TOUR_QUERY) === "1";
  const forceGuide = params.get(GUIDE_QUERY) === "1";
  const mounted = useSyncExternalStore(subscribeMount, () => true, () => false);
  const seen = useSyncExternalStore(subscribeTour, tourSeen, () => true);
  const usageSeen = useSyncExternalStore(subscribeGuide, guideSeen, () => true);
  const [replay, setReplay] = useState(false);
  const [dismissed, setDismissed] = useState(false);
  const [guideReplay, setGuideReplay] = useState(false);
  const [guideDismissed, setGuideDismissed] = useState(false);
  const storyOpen = mounted && !dismissed && (replay || forceTour || !seen);
  const guideOpen =
    mounted &&
    !storyOpen &&
    !guideDismissed &&
    (guideReplay || forceGuide || (seen && !usageSeen));

  function closeTour() {
    setReplay(false);
    setDismissed(true);
    if (!guideSeen()) {
      setGuideDismissed(false);
      setGuideReplay(true);
    }
  }

  function replayTour() {
    clearTourSeen();
    setGuideDismissed(true);
    setDismissed(false);
    setReplay(true);
  }

  function closeGuide() {
    setGuideReplay(false);
    setGuideDismissed(true);
  }

  function replayGuide() {
    clearGuideSeen();
    setDismissed(true);
    setGuideDismissed(false);
    setGuideReplay(true);
  }

  if (!mounted) {
    return <div className="min-h-screen bg-forest-deep" aria-hidden="true" />;
  }

  return (
    <div className="relative min-h-screen">
      <div
        className={`min-h-screen lg:grid lg:grid-cols-[248px_minmax(0,1fr)] ${
          storyOpen ? "pointer-events-none" : ""
        }`}
      >
        <aside className="bg-forest-deep text-paper-raised">
          <div className="flex h-full flex-col px-5 py-6">
            <div>
              <p className="text-[10px] font-medium uppercase tracking-[0.2em] text-white/45">
                Razorpay AI Buildathon · Track 03
              </p>
              <p className="mt-3 text-lg font-medium tracking-tight">AfterDue</p>
              <p className="mt-1 text-xs leading-5 text-white/60">
                Post-halt revenue intelligence for subscriptions.
              </p>
            </div>
            <nav className="mt-10 flex flex-col gap-1" aria-label="Primary">
              {PRIMARY_NAV.map((item) => {
                const active =
                  item.href === "/"
                    ? pathname === "/"
                    : pathname.startsWith(item.href);
                return (
                  <Link
                    key={item.href}
                    href={withRun(item.href, runId)}
                    data-guide={guideId(item.href)}
                    className={`rounded-md px-2.5 py-2 text-sm transition-colors ${
                      active
                        ? "bg-white/10 text-white"
                        : "text-white/65 hover:bg-white/5 hover:text-white"
                    }`}
                  >
                    {item.label}
                  </Link>
                );
              })}
            </nav>
            <div className="mt-8 border-t border-white/10 pt-4">
              <p className="mb-2 text-[10px] uppercase tracking-[0.16em] text-white/40">
                More
              </p>
              <Link
                href={withRun("/architecture", runId)}
                className={`block rounded-md px-2.5 py-2 text-sm ${
                  pathname.startsWith("/architecture")
                    ? "bg-white/10 text-white"
                    : "text-white/65 hover:bg-white/5 hover:text-white"
                }`}
              >
                Architecture
              </Link>
              <button
                type="button"
                onClick={replayGuide}
                className="mt-1 w-full rounded-md px-2.5 py-2 text-left text-sm text-white/65 hover:bg-white/5 hover:text-white"
              >
                How to use AfterDue
              </button>
              <button
                type="button"
                onClick={replayTour}
                className="mt-1 w-full rounded-md px-2.5 py-2 text-left text-sm text-white/65 hover:bg-white/5 hover:text-white"
              >
                Replay product tour
              </button>
            </div>
            <div className="mt-auto pt-8">{sidebarFooter}</div>
          </div>
        </aside>
        <div className="min-w-0">
          <div className="mx-auto max-w-6xl px-5 py-8 sm:px-8">{children}</div>
        </div>
      </div>
      {storyOpen ? <ProductTour onClose={closeTour} /> : null}
      {guideOpen ? <UsageGuide onClose={closeGuide} /> : null}
    </div>
  );
}
