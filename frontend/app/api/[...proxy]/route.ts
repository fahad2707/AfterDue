import { NextRequest, NextResponse } from "next/server";

import { API_URL, internalHeaders } from "@/lib/server-api";

/**
 * The only route the browser may use to reach the backend.
 *
 * Consequences that matter:
 *  - the backend origin and shared secret stay on the server
 *  - same-origin requests mean CORS is never a failure mode in the browser
 *  - the browser cannot invoke a backend path this proxy does not forward
 */

type RouteContext = { params: Promise<{ proxy: string[] }> };

const FORWARDED_REQUEST_HEADERS = ["content-type", "accept"];

async function forward(req: NextRequest, ctx: RouteContext) {
  const { proxy } = await ctx.params;
  const target = new URL(`/api/${proxy.join("/")}`, API_URL);
  target.search = req.nextUrl.search;

  const headers: Record<string, string> = {};
  for (const name of FORWARDED_REQUEST_HEADERS) {
    const value = req.headers.get(name);
    if (value) headers[name] = value;
  }

  const hasBody = req.method !== "GET" && req.method !== "HEAD";

  try {
    const res = await fetch(target, {
      method: req.method,
      headers: internalHeaders(headers),
      body: hasBody ? await req.text() : undefined,
      cache: "no-store",
    });

    const body = await res.text();
    return new NextResponse(body, {
      status: res.status,
      headers: {
        "content-type": res.headers.get("content-type") ?? "application/json",
      },
    });
  } catch (err) {
    return NextResponse.json(
      {
        detail: "backend unreachable",
        target: target.pathname,
        error: err instanceof Error ? err.message : String(err),
      },
      { status: 502 },
    );
  }
}

export const GET = forward;
export const POST = forward;
export const PATCH = forward;
export const DELETE = forward;
