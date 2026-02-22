import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import {
  fetchSquads,
  deleteSquad,
  type SavedSquad,
} from "../api/client";
import "./Dashboard.css";

export function MySquadsPage() {
  const { user, logout } = useAuth();
  const [squads, setSquads] = useState<SavedSquad[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchSquads()
      .then(setSquads)
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  async function handleDelete(id: number) {
    if (!confirm("Delete this squad?")) return;
    await deleteSquad(id);
    setSquads((prev) => prev.filter((s) => s.id !== id));
  }

  return (
    <div className="dashboard-page">
      <nav className="dashboard-nav">
        <Link to="/" className="dashboard-brand">⚽ Squad Builder</Link>
        <div className="dashboard-nav-links">
          <Link to="/builder">Builder</Link>
          <Link to="/squads" className="active">My Squads</Link>
          <Link to="/friends">Friends</Link>
          {user?.role === "admin" && <Link to="/admin">Admin</Link>}
          {user && <span className="dashboard-user">{user.display_name}</span>}
          {user && <button className="dashboard-logout" onClick={logout}>Log out</button>}
        </div>
      </nav>

      <div className="dashboard-content">
        <h1>My Saved Squads</h1>

        {loading && <p className="dashboard-info">Loading…</p>}

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
