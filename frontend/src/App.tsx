import { useEffect, useMemo, useState } from "react";
import "./App.css";

type Player = {
  player_id: number;
  name: string;
  position: string | null;
  nationality: string | null;
  date_of_birth: string | null; // ISO string or null
};

type PlayersResponse = {
  count: number;
  players: Player[];
};

function clampLimit(n: number) {
  if (Number.isNaN(n)) return 200;
  return Math.max(1, Math.min(2000, n));
}

export default function App() {
  const [nationality, setNationality] = useState("England");
  const [limit, setLimit] = useState(200);
  const [players, setPlayers] = useState<Player[]>([]);
  const [loading, setLoading] = useState(false);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const query = useMemo(() => {
    const params = new URLSearchParams();
    if (nationality.trim()) params.set("nationality", nationality.trim());
    params.set("limit", String(clampLimit(limit)));
    return params.toString();
  }, [nationality, limit]);

  async function loadPlayers() {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`/players?${query}`);
      if (!res.ok) {
        const text = await res.text();
        throw new Error(`GET /players failed (${res.status}): ${text}`);
      }
      const data = (await res.json()) as PlayersResponse;
      setPlayers(data.players);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setLoading(false);
    }
  }

  async function refreshData() {
    setRefreshing(true);
    setError(null);
    try {
      const res = await fetch("/refresh", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ competition: ["PL"] }),
      });
      if (!res.ok) {
        const text = await res.text();
        throw new Error(`POST /refresh failed (${res.status}): ${text}`);
      }
      await loadPlayers();
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setRefreshing(false);
    }
  }

  useEffect(() => {
    void loadPlayers();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [query]);

  return (
    <div style={{ maxWidth: 1100, margin: "0 auto", padding: 24 }}>
      <h1>Squad Builder</h1>

      <div style={{ display: "flex", gap: 12, alignItems: "end", flexWrap: "wrap", marginBottom: 16 }}>
        <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
          <label htmlFor="nat">Nationality</label>
          <input
            id="nat"
            value={nationality}
            onChange={(e) => setNationality(e.target.value)}
            placeholder="e.g. England"
            style={{ padding: "8px 10px", minWidth: 240 }}
          />
        </div>

        <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
          <label htmlFor="limit">Limit</label>
          <input
            id="limit"
            type="number"
            value={limit}
            onChange={(e) => setLimit(clampLimit(Number(e.target.value)))}
            min={1}
            max={2000}
            style={{ padding: "8px 10px", width: 120 }}
          />
        </div>

        <button
          onClick={refreshData}
          disabled={refreshing}
          style={{ padding: "10px 14px", cursor: refreshing ? "not-allowed" : "pointer" }}
        >
          {refreshing ? "Refreshing..." : "Refresh data"}
        </button>

        <div style={{ marginLeft: "auto", opacity: 0.8 }}>
          {loading ? "Loading..." : `${players.length} players`}
        </div>
      </div>

      {error && (
        <div style={{ background: "#fee", border: "1px solid #f99", padding: 12, borderRadius: 8, marginBottom: 16 }}>
          <strong>Error:</strong> {error}
        </div>
      )}

      <div style={{ overflowX: "auto", border: "1px solid #ddd", borderRadius: 10 }}>
        <table style={{ width: "100%", borderCollapse: "collapse" }}>
          <thead>
            <tr style={{ background: "#f7f7f7" }}>
              <th style={th}>ID</th>
              <th style={th}>Name</th>
              <th style={th}>Position</th>
              <th style={th}>Nationality</th>
              <th style={th}>DOB</th>
            </tr>
          </thead>
          <tbody>
            {players.map((p) => (
              <tr key={p.player_id}>
                <td style={td}>{p.player_id}</td>
                <td style={td}>{p.name}</td>
                <td style={td}>{p.position ?? "—"}</td>
                <td style={td}>{p.nationality ?? "—"}</td>
                <td style={td}>{p.date_of_birth ?? "—"}</td>
              </tr>
            ))}
            {players.length === 0 && !loading && (
              <tr>
                <td style={td} colSpan={5}>
                  No players found.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}

const th: React.CSSProperties = {
  textAlign: "left",
  padding: "10px 12px",
  borderBottom: "1px solid #ddd",
  fontWeight: 600,
};

const td: React.CSSProperties = {
  padding: "10px 12px",
  borderBottom: "1px solid #eee",
  whiteSpace: "nowrap",
};
