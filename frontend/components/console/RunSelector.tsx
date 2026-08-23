"use client";

import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { useTransition } from "react";

import { RUN_QUERY } from "@/lib/run";
import type { SimulationRun } from "@/types/api";

export function RunSelector({ runs }: { runs: SimulationRun[] }) {
  const router = useRouter();
  const pathname = usePathname();
  const params = useSearchParams();
  const [pending, start] = useTransition();
  const selected = params.get(RUN_QUERY) ?? runs[0]?.run_id ?? "";

  if (runs.length === 0) {
    return <p className="text-[11px] text-sand/70">No runs yet</p>;
  }

  return (
    <label className="block">
      <span className="mb-1.5 block text-[10px] uppercase tracking-[0.16em] text-sand/70">
        Simulation run
      </span>
      <select
        aria-label="Selected simulation run"
        className="w-full rounded-sm border border-white/15 bg-forest-deep px-2 py-1.5 font-mono text-[11px] text-paper-raised outline-none"
        value={selected}
        disabled={pending}
        onChange={(event) => {
          const next = new URLSearchParams(params.toString());
          next.set(RUN_QUERY, event.target.value);
          start(() => router.push(`${pathname}?${next.toString()}`));
        }}
      >
        {runs.map((run) => (
          <option key={run.run_id} value={run.run_id}>
            {run.run_id} · seed {run.seed}
          </option>
        ))}
      </select>
    </label>
  );
}
