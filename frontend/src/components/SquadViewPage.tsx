import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { fetchSquad, createSquad, type SquadDetail } from "../api/client";
import type { Player } from "../types/player";
import { positionGroup, GROUP_LABELS, type PositionGroup } from "../utils/positions";
import { NavBar } from "./NavBar";
import "./Dashboard.css";
import "./SquadView.css";

const GROUP_ORDER: PositionGroup[] = ["GK", "DEF", "MID", "FWD", "OTHER"];

function groupPlayers(players: Player[]): Record<PositionGroup, Player[]> {
  const groups: Record<PositionGroup, Player[]> = { GK: [], DEF: [], MID: [], FWD: [], OTHER: [] };
  for (const p of players) groups[positionGroup(p.position)].push(p);
  return groups;
}

/* ── Component ────────────────────────────────────────────────────── */

export function SquadViewPage() {
  const { user } = useAuth();
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();

  const [squad, setSquad] = useState<SquadDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [saveMsg, setSaveMsg] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  const isOwner = !!(user && squad && squad.owner_id === user.id);

  useEffect(() => {
    if (!id) return;
    fetchSquad(Number(id))
      .then(setSquad)
      .catch((e) => setError(e instanceof Error ? e.message : "Failed to load squad"))
      .finally(() => setLoading(false));
  }, [id]);

  function handleEdit() {
    if (!squad) return;
    navigate("/builder", { state: { editSquadId: squad.id, editPlayerIds: squad.player_ids, editSquadName: squad.name } });
  }

  async function handleSaveToMySquads() {
    if (!squad) return;
    setSaving(true);
    setSaveMsg(null);
    try {
      const name = `${squad.owner_name}-${squad.name}`;
      await createSquad(name, squad.player_ids);
      setSaveMsg("Saved to your squads!");
    } catch (err) {
      setSaveMsg(err instanceof Error ? err.message : "Save failed");
    } finally {
      setSaving(false);
    }
  }

  if (loading) {
    return (
      <div className="dashboard-page">
        <NavBar active="squads" />
        <div className="dashboard-content"><p className="dashboard-info">Loading…</p></div>
      </div>
    );
  }

  if (error || !squad) {
    return (
      <div className="dashboard-page">
        <NavBar active="squads" />
        <div className="dashboard-content">
          <p className="dashboard-error">{error ?? "Squad not found"}</p>
          <Link to="/squads" className="dashboard-cta" style={{ marginTop: "1rem", display: "inline-block" }}>← Back to squads</Link>
        </div>
      </div>
    );
  }

  const grouped = groupPlayers(squad.players);

  return (
    <div className="dashboard-page">
      <NavBar active="squads" />

      <div className="sv-content">
        <div className="sv-header">
          <div>
            <h1 className="sv-title">{squad.name}</h1>
            <p className="sv-meta">
              {squad.players.length} players · Saved {new Date(squad.created_at).toLocaleDateString()}
            </p>
          </div>
          <div className="sv-actions">
            {isOwner ? (
              <button className="sv-edit-btn" onClick={handleEdit}>✏️ Edit in Builder</button>
            ) : (
              <button
                className="sv-edit-btn"
                onClick={handleSaveToMySquads}
                disabled={saving}
              >
                {saving ? "Saving…" : "💾 Save to your squads"}
              </button>
            )}
            {saveMsg && <span className={saveMsg.includes("Saved") ? "dashboard-success" : "dashboard-error"} style={{ fontSize: "0.85rem" }}>{saveMsg}</span>}
            <Link to={isOwner ? "/squads" : "/friends"} className="sv-back-link">
              ← {isOwner ? "All Squads" : "Back to Friends"}
            </Link>
          </div>
        </div>

        <div className="sv-roster">
          {GROUP_ORDER.map((g) =>
            grouped[g].length > 0 ? (
              <div key={g} className="sv-roster-group">
                <h3>{GROUP_LABELS[g]} ({grouped[g].length})</h3>
                <div className="sv-roster-list">
                  {grouped[g].sort((a, b) => a.name.localeCompare(b.name)).map((p) => (
                    <div key={p.player_id} className="sv-roster-row">
                      <strong>{p.name}</strong>
                      <span className="sv-roster-meta">{p.position}</span>
                      <span className="sv-roster-meta">{p.nationality}</span>
                    </div>
                  ))}
                </div>
              </div>
            ) : null
          )}
        </div>
      </div>
    </div>
  );
}
