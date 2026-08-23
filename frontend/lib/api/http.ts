export class ApiError extends Error {
  constructor(
    message: string,
    readonly status: number,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

async function parse(res: Response): Promise<unknown> {
  const text = await res.text();
  if (!text) return null;
  try {
    return JSON.parse(text);
  } catch {
    return { detail: text.slice(0, 200) };
  }
}

function detailOf(body: unknown, fallback: string): string {
  if (typeof body === "object" && body !== null && "detail" in body) {
    return String((body as { detail: unknown }).detail);
  }
  return fallback;
}

export async function apiGet<T>(path: string): Promise<T> {
  const res = await fetch(path, { cache: "no-store" });
  const body = await parse(res);
  if (!res.ok) {
    throw new ApiError(
      detailOf(body, res.status === 0 ? "Backend is currently unavailable." : "Request failed."),
      res.status,
    );
  }
  return body as T;
}

export async function apiPost<T>(path: string, payload: unknown): Promise<T> {
  const res = await fetch(path, {
    method: "POST",
    headers: { "content-type": "application/json", accept: "application/json" },
    body: JSON.stringify(payload),
    cache: "no-store",
  });
  const body = await parse(res);
  if (!res.ok) {
    throw new ApiError(
      detailOf(
        body,
        res.status >= 500
          ? "Backend is currently unavailable."
          : "The request could not be completed.",
      ),
      res.status,
    );
  }
  return body as T;
}
