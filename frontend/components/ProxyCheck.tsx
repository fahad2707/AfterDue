"use client";

import { useEffect, useState } from "react";

import type { MetaResponse } from "@/types/api";

type State =
  | { phase: "loading" }
  | { phase: "ok"; data: MetaResponse }
  | { phase: "error"; message: string };

/**
 * Proves the browser -> Next proxy -> FastAPI path. This component holds no
 * backend URL and no secret; it can only call same-origin /api/meta.
 */
export function ProxyCheck() {
  const [state, setState] = useState<State>({ phase: "loading" });

  useEffect(() => {
    fetch("/api/meta")
      .then(async (res) => {
        const body = await res.json();
        if (!res.ok) throw new Error(body.detail ?? `HTTP ${res.status}`);
        setState({ phase: "ok", data: body as MetaResponse });
      })
      .catch((err: Error) => setState({ phase: "error", message: err.message }));
  }, []);

  if (state.phase === "loading") {
    return <Row label="browser → proxy → api" value="checking…" tone="muted" />;
  }

  if (state.phase === "error") {
    return <Row label="browser → proxy → api" value={state.message} tone="bad" />;
  }

  return (
    <Row
      label="browser → proxy → api"
      value={`${state.data.service} · policy ${state.data.policy_version}`}
      tone="good"
    />
  );
}

function Row({
  label,
  value,
  tone,
}: {
  label: string;
  value: string;
  tone: "good" | "bad" | "muted";
}) {
  const dot =
    tone === "good"
      ? "bg-emerald-500"
      : tone === "bad"
        ? "bg-red-500"
        : "bg-neutral-400";

  return (
    <div className="flex items-center justify-between gap-4 border-t border-neutral-200 py-3 text-sm dark:border-neutral-800">
      <span className="text-neutral-500 dark:text-neutral-400">{label}</span>
      <span className="flex items-center gap-2 font-mono text-xs text-neutral-900 dark:text-neutral-100">
        <span className={`h-1.5 w-1.5 rounded-full ${dot}`} />
        {value}
      </span>
    </div>
  );
}
