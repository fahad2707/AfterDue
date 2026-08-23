export const RUN_QUERY = "run";

export function withRun(pathname: string, runId: string | null | undefined): string {
  if (!runId) return pathname;
  const params = new URLSearchParams();
  params.set(RUN_QUERY, runId);
  return `${pathname}?${params.toString()}`;
}

export function scopedQuery(runId: string): string {
  return `run_id=${encodeURIComponent(runId)}`;
}
