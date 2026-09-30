const API_URL = (process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000").replace(/\/+$/, "");

function requestHeaders(initial?: HeadersInit): Headers {
  const result = new Headers(initial);
  const key = typeof window !== "undefined" ? localStorage.getItem("shodh-api-key") : null;
  if (key && !result.has("X-API-Key")) result.set("X-API-Key", key);
  return result;
}

export async function api<T>(path: string, init: RequestInit = {}): Promise<T> {
  const response = await fetch(`${API_URL}${path}`, {
    ...init,
    headers: requestHeaders(init.headers),
  });
  if (!response.ok) {
    const body = await response.text();
    throw new Error(body || `Request failed (${response.status})`);
  }
  if (response.status === 204) return undefined as T;
  return response.json();
}

export function uploadUrl() {
  return `${API_URL}/ingest`;
}
