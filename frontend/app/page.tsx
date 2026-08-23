import { ProxyCheck } from "@/components/ProxyCheck";
import { apiGet } from "@/lib/server-api";
import type { HealthResponse, MetaResponse, ReadyResponse } from "@/types/api";

export const dynamic = "force-dynamic";

export default async function Home() {
  const [health, ready, meta] = await Promise.all([
    apiGet<HealthResponse>("/healthz"),
    apiGet<ReadyResponse>("/readyz", [503]),
    apiGet<MetaResponse>("/api/meta"),
  ]);

  const mongo = ready.ok ? ready.data.checks.mongodb : null;

  return (
    <main className="mx-auto flex min-h-screen max-w-2xl flex-col justify-center px-6 py-16">
      <header className="mb-10">
        <div className="mb-3 inline-flex items-center rounded-full border border-amber-300 bg-amber-50 px-2.5 py-1 text-[11px] font-medium uppercase tracking-wide text-amber-800 dark:border-amber-800/60 dark:bg-amber-950/40 dark:text-amber-300">
          Synthetic simulation — not production data
        </div>
        <h1 className="text-2xl font-semibold tracking-tight text-neutral-900 dark:text-neutral-50">
          RECLAIM
        </h1>
        <p className="mt-1 text-sm text-neutral-500 dark:text-neutral-400">
          Recover stranded subscription revenue after customers return.
        </p>
      </header>

      <section>
        <h2 className="mb-1 text-xs font-medium uppercase tracking-wide text-neutral-400">
          M0 — foundation checks
        </h2>

        <StatusRow
          label="api liveness /healthz"
          value={health.ok ? `${health.data.status} · ${health.data.app_env}` : health.error}
          ok={health.ok}
        />
        <StatusRow
          label="api readiness /readyz"
          value={ready.ok ? (ready.data.ready ? "ready" : "not ready") : ready.error}
          ok={ready.ok && ready.data.ready}
        />
        <StatusRow
          label="mongodb atlas"
          value={mongo ? (mongo.ok ? "connected" : (mongo.detail ?? "unreachable")) : "unknown"}
          ok={Boolean(mongo?.ok)}
        />
        <StatusRow
          label="server → api"
          value={meta.ok ? `llm_enabled=${meta.data.llm_enabled}` : meta.error}
          ok={meta.ok}
        />
        <ProxyCheck />
      </section>
    </main>
  );
}

function StatusRow({
  label,
  value,
  ok,
}: {
  label: string;
  value: string;
  ok: boolean;
}) {
  return (
    <div className="flex items-center justify-between gap-4 border-t border-neutral-200 py-3 text-sm dark:border-neutral-800">
      <span className="text-neutral-500 dark:text-neutral-400">{label}</span>
      <span className="flex items-center gap-2 font-mono text-xs text-neutral-900 dark:text-neutral-100">
        <span
          className={`h-1.5 w-1.5 rounded-full ${ok ? "bg-emerald-500" : "bg-red-500"}`}
        />
        <span className="max-w-[22rem] truncate">{value}</span>
      </span>
    </div>
  );
}
