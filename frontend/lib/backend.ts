import type { RouteRequest, RouteResponse, VerifyResponse } from "./types";

const BACKEND_URL =
  process.env.NEXT_PUBLIC_BACKEND_URL?.replace(/\/$/, "") ||
  "http://localhost:8000";

// The backend is keyless: we send only the transcript + conversation state.
// API keys never go here — they go straight from the browser to the providers.
export async function routeTurn(req: RouteRequest): Promise<RouteResponse> {
  const res = await fetch(`${BACKEND_URL}/route`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(req),
  });
  if (!res.ok) throw new Error(`Backend /route ${res.status}`);
  return (await res.json()) as RouteResponse;
}

export async function verifyAnswer(
  response: string,
  context_str: string,
): Promise<VerifyResponse> {
  const res = await fetch(`${BACKEND_URL}/verify`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ response, context_str }),
  });
  if (!res.ok) throw new Error(`Backend /verify ${res.status}`);
  return (await res.json()) as VerifyResponse;
}

export async function backendHealth(): Promise<{
  status: string;
  slides: number;
  chunks: number;
  live_model: string;
}> {
  const res = await fetch(`${BACKEND_URL}/health`);
  if (!res.ok) throw new Error(`Backend /health ${res.status}`);
  return await res.json();
}

export { BACKEND_URL };
