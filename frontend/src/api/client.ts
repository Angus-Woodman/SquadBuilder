import type { PlayersResponse } from "../types/player";

export async function fetchPlayers(params: {
  nationality?: string;
  limit?: number;
}): Promise<PlayersResponse> {
  const qs = new URLSearchParams();
  if (params.nationality?.trim()) qs.set("nationality", params.nationality.trim());
  if (params.limit) qs.set("limit", String(params.limit));

  const res = await fetch(`/players?${qs.toString()}`);
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`GET /players failed (${res.status}): ${text}`);
  }
  return (await res.json()) as PlayersResponse;
}

export async function refreshData(competition: string[] = ["PL"]): Promise<void> {
  const res = await fetch("/refresh", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ competition }),
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`POST /refresh failed (${res.status}): ${text}`);
  }
}
