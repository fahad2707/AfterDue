import "server-only";

/**
 * Server-side access to the RECLAIM backend.
 *
 * RECLAIM_API_URL and INTERNAL_API_KEY are deliberately NOT prefixed with
 * NEXT_PUBLIC_, so they never reach the browser bundle. Server Components use
 * these helpers; Client Components go through /api/* which proxies here.
 */

export const API_URL = process.env.RECLAIM_API_URL ?? "http://127.0.0.1:8000";
const INTERNAL_API_KEY = process.env.INTERNAL_API_KEY ?? "";

export function internalHeaders(extra: HeadersInit = {}): HeadersInit {
  return INTERNAL_API_KEY
    ? { ...extra, "x-internal-api-key": INTERNAL_API_KEY }
    : extra;
}

export type FetchResult<T> =
  | { ok: true; status: number; data: T }
  | { ok: false; status: number; error: string };

/**
 * `alsoAccept` lets a caller treat a non-2xx status as a valid payload.
 * /readyz answers 503 with a body that describes *which* dependency failed,
 * and that body is the whole point.
 */
export async function apiGet<T>(
  path: string,
  alsoAccept: number[] = [],
): Promise<FetchResult<T>> {
  try {
    const res = await fetch(new URL(path, API_URL), {
      headers: internalHeaders({ accept: "application/json" }),
      cache: "no-store",
    });

    const text = await res.text();
    let parsed: unknown;
    try {
      parsed = JSON.parse(text);
    } catch {
      return { ok: false, status: res.status, error: text.slice(0, 200) };
    }

    if (!res.ok && !alsoAccept.includes(res.status)) {
      const detail =
        typeof parsed === "object" && parsed !== null && "detail" in parsed
          ? String((parsed as { detail: unknown }).detail)
          : `HTTP ${res.status}`;
      return { ok: false, status: res.status, error: detail };
    }

    return { ok: true, status: res.status, data: parsed as T };
  } catch (err) {
    return {
      ok: false,
      status: 0,
      error: err instanceof Error ? err.message : "unreachable",
    };
  }
}
