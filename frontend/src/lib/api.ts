/**
 * Thin client for the EduBridge gateway.
 *
 * Every request goes to same-origin `/api/<service>/...`; `next.config.ts`
 * rewrites that to Traefik, which strips `/api` and routes by service prefix.
 * Access tokens are short-lived (15 min), so a 401 triggers one refresh attempt
 * and a replay of the original request.
 */

export const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? "/api";

const ACCESS_KEY = "eb.access";
const REFRESH_KEY = "eb.refresh";

export type TokenPair = {
  access_token: string;
  refresh_token: string;
  token_type: string;
};

export class ApiError extends Error {
  constructor(
    readonly status: number,
    message: string,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

export const tokens = {
  access: () => (typeof window === "undefined" ? null : localStorage.getItem(ACCESS_KEY)),
  refresh: () => (typeof window === "undefined" ? null : localStorage.getItem(REFRESH_KEY)),
  save(pair: TokenPair) {
    localStorage.setItem(ACCESS_KEY, pair.access_token);
    localStorage.setItem(REFRESH_KEY, pair.refresh_token);
    window.dispatchEvent(new Event("eb:auth"));
  },
  clear() {
    localStorage.removeItem(ACCESS_KEY);
    localStorage.removeItem(REFRESH_KEY);
    window.dispatchEvent(new Event("eb:auth"));
  },
};

/** FastAPI returns `detail` as a string or as a list of validation objects. */
function messageFrom(status: number, body: unknown): string {
  const detail = (body as { detail?: unknown } | null)?.detail;
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    const first = detail[0] as { msg?: string; loc?: unknown[] } | undefined;
    if (first?.msg) {
      const field = Array.isArray(first.loc) ? first.loc[first.loc.length - 1] : undefined;
      return field ? `${field}: ${first.msg}` : first.msg;
    }
  }
  return `Ошибка запроса (${status})`;
}

type Options = Omit<RequestInit, "body"> & { body?: unknown; auth?: boolean };

async function raw(path: string, options: Options = {}): Promise<Response> {
  const { body, auth = false, headers, ...rest } = options;
  const h = new Headers(headers);
  if (body !== undefined) h.set("Content-Type", "application/json");
  if (auth) {
    const token = tokens.access();
    if (token) h.set("Authorization", `Bearer ${token}`);
  }
  return fetch(`${API_BASE}${path}`, {
    ...rest,
    headers: h,
    body: body === undefined ? undefined : JSON.stringify(body),
  });
}

let refreshing: Promise<boolean> | null = null;

async function tryRefresh(): Promise<boolean> {
  const token = tokens.refresh();
  if (!token) return false;
  // Collapse parallel 401s into a single refresh round-trip.
  refreshing ??= (async () => {
    try {
      const res = await raw("/auth/refresh", { method: "POST", body: { refresh_token: token } });
      if (res.ok) {
        tokens.save((await res.json()) as TokenPair);
        return true;
      }
      // Only a definitive "this refresh token is no good" answer ends the
      // session. Anything else (502/503 mid-deploy, a Redis blip, a dropped
      // connection surfacing as 500) must NOT wipe a still-valid refresh
      // token — the previous behavior logged everyone out on any refresh
      // hiccup, which lined up with every backend deploy (auto-triggered on
      // push to master) since a request that landed mid-restart got a
      // transient error instead of a real "token revoked" answer.
      if (res.status === 401 || res.status === 403 || res.status === 422) {
        tokens.clear();
      }
      return false;
    } catch {
      // Network failure reaching /auth/refresh at all — same reasoning,
      // don't clear tokens on a connectivity blip.
      return false;
    } finally {
      // Reset on the next tick so concurrent callers share this attempt.
      setTimeout(() => (refreshing = null), 0);
    }
  })();
  return refreshing;
}

export async function api<T>(path: string, options: Options = {}): Promise<T> {
  let res = await raw(path, options);

  if (res.status === 401 && options.auth && (await tryRefresh())) {
    res = await raw(path, options);
  }

  if (res.status === 204) return undefined as T;

  const text = await res.text();
  const parsed = text ? (JSON.parse(text) as unknown) : null;

  if (!res.ok) throw new ApiError(res.status, messageFrom(res.status, parsed));
  return parsed as T;
}

export const get = <T,>(path: string, auth = false) => api<T>(path, { auth });
export const post = <T,>(path: string, body?: unknown, auth = false) =>
  api<T>(path, { method: "POST", body, auth });
export const put = <T,>(path: string, body?: unknown, auth = false) =>
  api<T>(path, { method: "PUT", body, auth });
export const del = <T,>(path: string, auth = true) => api<T>(path, { method: "DELETE", auth });
