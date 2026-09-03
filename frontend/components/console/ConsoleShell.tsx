import { Suspense, type ReactNode } from "react";

import { AppFrame } from "@/components/console/AppFrame";
import { RunSelector } from "@/components/console/RunSelector";
import { SyntheticBadge } from "@/components/console/SyntheticBadge";
import { apiGet } from "@/lib/server-api";
import type { SimulationRun } from "@/types/api";

export async function ConsoleShell({ children }: { children: ReactNode }) {
  const runs = await apiGet<SimulationRun[]>("/api/runs");
  const list = runs.ok ? runs.data : [];

  return (
    <AppFrame
      sidebarFooter={
        <>
          <div className="mb-3">
            <SyntheticBadge />
          </div>
          <Suspense fallback={null}>
            <RunSelector runs={list} />
          </Suspense>
          {!runs.ok ? (
            <p className="mt-3 text-[11px] leading-5 text-white/50">
              Backend is currently unavailable. Run data cannot be loaded.
            </p>
          ) : null}
        </>
      }
    >
      {children}
    </AppFrame>
  );
}
