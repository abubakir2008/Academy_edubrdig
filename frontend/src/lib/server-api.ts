/**
 * Server-side reads of public endpoints. Server components cannot use the
 * relative `/api` rewrite, so they call the gateway directly. Every helper
 * degrades to a safe empty value: the marketing pages must render even when the
 * backend stack is down.
 */

const GATEWAY = process.env.API_GATEWAY_URL ?? "http://localhost";

export async function fetchPublic<T>(path: string, fallback: T, revalidate = 60): Promise<T> {
  try {
    const res = await fetch(`${GATEWAY}/api${path}`, {
      next: { revalidate },
      signal: AbortSignal.timeout(4000),
    });
    if (!res.ok) return fallback;
    return (await res.json()) as T;
  } catch {
    return fallback;
  }
}
