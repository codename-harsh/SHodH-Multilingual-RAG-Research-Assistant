const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

function headers() {
  const key = typeof window !== "undefined" ? localStorage.getItem("shodh-api-key") : null;
  return key ? { "X-API-Key": key } : {};
}

export async function api<T>(path: string, init: RequestInit = {}): Promise<T> {
  const response = await fetch(`${API_URL}${path}`, {
    ...init,
    headers: { ...headers(), ...(init.headers ?? {}) },
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
