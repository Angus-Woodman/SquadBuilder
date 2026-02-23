import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import {
  fetchSquads,
  deleteSquad,
  type SavedSquad,
} from "../api/client";
import { NavBar } from "./NavBar";
import "./Dashboard.css";

export function MySquadsPage() {
  const [squads, setSquads] = useState<SavedSquad[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchSquads()
      .then(setSquads)
      .catch((e) => setError(e instanceof Error ? e.message : "Failed to load squads"))
      .finally(() => setLoading(false));
  }, []);

  async function handleDelete(id: number) {
    if (!confirm("Delete this squad?")) return;
    try {
      await deleteSquad(id);
      setSquads((prev) => prev.filter((s) => s.id !== id));
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to delete squad");
    }
  }

  return (
    <div className="dashboard-page">
      <NavBar active="squads" />

      <div className="dashboard-content">
        <h1>My Saved Squads</h1>

        {loading && <p className="dashboard-info">Loading…</p>}
        {error && <p className="dashboard-error">{error}</p>}

        {!loading && squads.length === 0 && (
          <div className="dashboard-empty">
            <p>You haven't saved any squads yet.</p>
            <Link to="/builder" className="dashboard-cta">Build your first squad →</Link>
          </div>
        )}

        <div className="squad-grid">
          {squads.map((s) => (
            <Link key={s.id} to={`/squads/${s.id}`} className="squad-card squad-card-link">
              <div className="squad-card-header">
                <h3>{s.name}</h3>
                <button
                  className="squad-card-delete"
                  onClick={(e) => { e.preventDefault(); e.stopPropagation(); handleDelete(s.id); }}
                  title="Delete squad"
                >
                  ✕
                </button>
              </div>
              <p className="squad-card-meta">
                {s.player_ids.length} players · {new Date(s.created_at).toLocaleDateString()}
              </p>
            </Link>
          ))}
        </div>
      </div>
    </div>
  );
}
