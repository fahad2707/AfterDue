import { Suspense, type ReactNode } from "react";

import { NavLinks } from "@/components/console/NavLinks";
import { RunSelector } from "@/components/console/RunSelector";
import { SyntheticBadge } from "@/components/console/SyntheticBadge";
import { apiGet } from "@/lib/server-api";
import type { SimulationRun } from "@/types/api";

export async function ConsoleShell({ children }: { children: ReactNode }) {
  const runs = await apiGet<SimulationRun[]>("/api/runs");
  const list = runs.ok ? runs.data : [];

  return (
    <div className="min-h-screen lg:grid lg:grid-cols-[240px_minmax(0,1fr)]">
      <aside className="bg-forest-deep text-paper-raised">
        <div className="flex h-full flex-col px-5 py-6">
          <div>
            <p className="font-mono text-[11px] uppercase tracking-[0.22em] text-sand/80">
              Reclaim
            </p>
            <h1 className="mt-2 text-lg font-medium tracking-tight">
              Post-halt revenue recovery
            </h1>
            <div className="mt-3">
              <SyntheticBadge />
            </div>
          </div>
          <Suspense fallback={null}>
            <NavLinks />
          </Suspense>
          <div className="mt-auto pt-8">
            <Suspense fallback={null}>
              <RunSelector runs={list} />
            </Suspense>
            {!runs.ok ? (
              <p className="mt-3 text-[11px] leading-5 text-sand/70">
                Backend is currently unavailable. Run data cannot be loaded.
              </p>
            ) : null}
          </div>
        </div>
      </aside>
      <div className="min-w-0">
        <div className="mx-auto max-w-6xl px-5 py-8 sm:px-8">{children}</div>
      </div>
    </div>
  );
}
