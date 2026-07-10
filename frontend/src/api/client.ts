import type { PlayersResponse } from "../types/player";

// ── Base URL prefix ──────────────────────────────────────────────────

const API = import.meta.env.VITE_API_BASE ?? "/api";

// ── Token management ─────────────────────────────────────────────────

const TOKEN_KEY = "squad-builder:token";

export function getStoredToken(): string | null {
  return localStorage.getItem(TOKEN_KEY);
}

export function storeToken(token: string): void {
  localStorage.setItem(TOKEN_KEY, token);
}

export function clearToken(): void {
  localStorage.removeItem(TOKEN_KEY);
}

function authHeaders(): Record<string, string> {
  const token = getStoredToken();
  return token ? { Authorization: `Bearer ${token}` } : {};
}

// ── Player endpoints (public) ────────────────────────────────────────

export async function fetchPlayers(
  params: { nationality?: string; limit?: number },
  signal?: AbortSignal,
): Promise<PlayersResponse> {
  const qs = new URLSearchParams();
  if (params.nationality?.trim()) qs.set("nationality", params.nationality.trim());
  if (params.limit) qs.set("limit", String(params.limit));

  const res = await fetch(`${API}/players?${qs.toString()}`, { signal });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`GET /players failed (${res.status}): ${text}`);
  }
  return (await res.json()) as PlayersResponse;
}

export async function refreshData(competition: string[] = ["PL"]): Promise<void> {
  const res = await fetch(`${API}/refresh`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...authHeaders() },
    body: JSON.stringify({ competition }),
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`POST /refresh failed (${res.status}): ${text}`);
  }
}

export async function fetchSuggestedIds(): Promise<number[]> {
  const res = await fetch(`${API}/suggested`);
  if (!res.ok) return [];
  const data = await res.json();
  return data.player_ids ?? [];
}

// ── Auth endpoints ───────────────────────────────────────────────────

export type AuthResponse = { access_token: string; token_type: string };
export type UserInfo = {
  id: number;
  email: string;
  display_name: string;
  role: string;
  created_at: string;
};

export async function register(
  email: string,
  displayName: string,
  password: string,
): Promise<AuthResponse> {
  const res = await fetch(`${API}/auth/register`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, display_name: displayName, password }),
  });
  if (!res.ok) {
    const data = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(data.detail || "Registration failed");
  }
  return res.json();
}

export async function login(email: string, password: string): Promise<AuthResponse> {
  const res = await fetch(`${API}/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });
  if (!res.ok) {
    const data = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(data.detail || "Login failed");
  }
  return res.json();
}

export async function fetchMe(): Promise<UserInfo> {
  const res = await fetch(`${API}/auth/me`, { headers: authHeaders() });
  if (!res.ok) throw new Error("Not authenticated");
  return res.json();
}

// ── Squad endpoints ──────────────────────────────────────────────────

export type SavedSquad = {
  id: number;
  name: string;
  player_ids: number[];
  created_at: string;
};

export type SquadDetail = SavedSquad & {
  owner_id: number;
  owner_name: string;
  players: import("../types/player").Player[];
};

export async function fetchSquads(): Promise<SavedSquad[]> {
  const res = await fetch(`${API}/squads/`, { headers: authHeaders() });
  if (!res.ok) throw new Error("Failed to load squads");
  return res.json();
}

export async function fetchSquad(squadId: number): Promise<SquadDetail> {
  const res = await fetch(`${API}/squads/${squadId}`, { headers: authHeaders() });
  if (!res.ok) throw new Error("Failed to load squad");
  return res.json();
}

export async function createSquad(name: string, playerIds: number[]): Promise<SavedSquad> {
  const res = await fetch(`${API}/squads/`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...authHeaders() },
    body: JSON.stringify({ name, player_ids: playerIds }),
  });
  if (!res.ok) {
    const data = await res.json().catch(() => ({ detail: "Save failed" }));
    throw new Error(data.detail);
  }
  return res.json();
}

export async function updateSquad(squadId: number, name: string, playerIds: number[]): Promise<SavedSquad> {
  const res = await fetch(`${API}/squads/${squadId}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json", ...authHeaders() },
    body: JSON.stringify({ name, player_ids: playerIds }),
  });
  if (!res.ok) {
    const data = await res.json().catch(() => ({ detail: "Update failed" }));
    throw new Error(data.detail);
  }
  return res.json();
}

export async function deleteSquad(squadId: number): Promise<void> {
  const res = await fetch(`${API}/squads/${squadId}`, {
    method: "DELETE",
    headers: authHeaders(),
  });
  if (!res.ok) throw new Error("Failed to delete squad");
}

// ── Friend endpoints ─────────────────────────────────────────────────

export type FriendInfo = {
  friendship_id: number;
  user_id: number;
  display_name: string;
  email: string;
  status: string;
  direction: string;
};

export async function fetchFriends(): Promise<FriendInfo[]> {
  const res = await fetch(`${API}/friends/`, { headers: authHeaders() });
  if (!res.ok) throw new Error("Failed to load friends");
  return res.json();
}

export async function sendFriendRequest(email: string): Promise<FriendInfo> {
  const res = await fetch(`${API}/friends/request`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...authHeaders() },
    body: JSON.stringify({ email }),
  });
  if (!res.ok) {
    const data = await res.json().catch(() => ({ detail: "Request failed" }));
    throw new Error(data.detail);
  }
  return res.json();
}

export async function acceptFriendRequest(friendshipId: number): Promise<FriendInfo> {
  const res = await fetch(`${API}/friends/${friendshipId}/accept`, {
    method: "PUT",
    headers: authHeaders(),
  });
  if (!res.ok) throw new Error("Failed to accept request");
  return res.json();
}

export async function removeFriend(friendshipId: number): Promise<void> {
  const res = await fetch(`${API}/friends/${friendshipId}`, {
    method: "DELETE",
    headers: authHeaders(),
  });
  if (!res.ok) throw new Error("Failed to remove friend");
}

export async function fetchFriendSquads(friendUserId: number): Promise<SavedSquad[]> {
  const res = await fetch(`${API}/friends/${friendUserId}/squads`, { headers: authHeaders() });
  if (!res.ok) throw new Error("Failed to load friend squads");
  return res.json();
}

// ── Admin endpoints ──────────────────────────────────────────────────

export type AdminSuggestedPlayer = {
  player_id: number;
  name: string;
  position: string | null;
  nationality: string | null;
};

export type AdminUser = {
  id: number;
  email: string;
  display_name: string;
  role: string;
  created_at: string;
};

export async function adminGetSuggested(): Promise<AdminSuggestedPlayer[]> {
  const res = await fetch(`${API}/admin/suggested`, { headers: authHeaders() });
  if (!res.ok) throw new Error("Failed to load suggested list");
  return res.json();
}

export async function adminSetSuggested(playerIds: number[]): Promise<void> {
  const res = await fetch(`${API}/admin/suggested`, {
    method: "PUT",
    headers: { "Content-Type": "application/json", ...authHeaders() },
    body: JSON.stringify({ player_ids: playerIds }),
  });
  if (!res.ok) throw new Error("Failed to update suggested list");
}

export async function adminGetUsers(): Promise<AdminUser[]> {
  const res = await fetch(`${API}/admin/users`, { headers: authHeaders() });
  if (!res.ok) throw new Error("Failed to load users");
  return res.json();
}

export async function adminSetUserRole(userId: number, role: string): Promise<void> {
  const res = await fetch(`${API}/admin/users/${userId}/role?role=${role}`, {
    method: "PUT",
    headers: authHeaders(),
  });
  if (!res.ok) throw new Error("Failed to update user role");
}

export async function adminCreateUser(
  email: string,
  displayName: string,
  password: string,
  role: string,
): Promise<AdminUser> {
  const res = await fetch(`${API}/admin/users`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...authHeaders() },
    body: JSON.stringify({ email, display_name: displayName, password, role }),
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail || "Failed to create user");
  }
  return res.json();
}

export async function adminDeleteUser(userId: number): Promise<void> {
  const res = await fetch(`${API}/admin/users/${userId}`, {
    method: "DELETE",
    headers: authHeaders(),
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail || "Failed to delete user");
  }
}

export type AdminPlayer = {
  player_id: number;
  name: string;
  position: string | null;
  nationality: string | null;
  date_of_birth: string | null;
};

export async function adminSearchPlayers(query: string): Promise<AdminPlayer[]> {
  const res = await fetch(`${API}/admin/players/search?q=${encodeURIComponent(query)}`, {
    headers: authHeaders(),
  });
  if (!res.ok) throw new Error("Failed to search players");
  return res.json();
}

export async function adminUpdatePlayer(
  playerId: number,
  data: Partial<Omit<AdminPlayer, "player_id">>,
): Promise<AdminPlayer> {
  const res = await fetch(`${API}/admin/players/${playerId}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json", ...authHeaders() },
    body: JSON.stringify(data),
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail || "Failed to update player");
  }
  return res.json();
}
