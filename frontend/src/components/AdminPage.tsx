import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import {
  adminGetSuggested,
  adminGetUsers,
  adminSetUserRole,
  adminCreateUser,
  adminDeleteUser,
  adminSearchPlayers,
  adminUpdatePlayer,
  fetchPlayers,
  adminSetSuggested,
  refreshData,
  type AdminSuggestedPlayer,
  type AdminUser,
  type AdminPlayer,
} from "../api/client";
import type { Player } from "../types/player";
import { loadSuggestedIds } from "../utils/storage";
import "./Dashboard.css";
import "./AdminPage.css";

type Tab = "suggested" | "users" | "players" | "data";

export function AdminPage() {
  const { user, logout } = useAuth();
  const [tab, setTab] = useState<Tab>("suggested");

  return (
    <div className="dashboard-page">
      <nav className="dashboard-nav">
        <Link to="/" className="dashboard-brand">⚽ Squad Builder</Link>
        <div className="dashboard-nav-links">
          <Link to="/builder">Builder</Link>
          <Link to="/squads">My Squads</Link>
          <Link to="/friends">Friends</Link>
          <Link to="/admin" className="active">Admin</Link>
          {user && <span className="dashboard-user">{user.display_name}</span>}
          {user && <button className="dashboard-logout" onClick={logout}>Log out</button>}
        </div>
      </nav>

      <div className="dashboard-content">
        <h1>Admin Panel</h1>

        <div className="admin-tabs">
          <button className={tab === "suggested" ? "active" : ""} onClick={() => setTab("suggested")}>
            Suggested Players
          </button>
          <button className={tab === "users" ? "active" : ""} onClick={() => setTab("users")}>
            Users
          </button>
          <button className={tab === "players" ? "active" : ""} onClick={() => setTab("players")}>
            Players
          </button>
          <button className={tab === "data" ? "active" : ""} onClick={() => setTab("data")}>
            Data
          </button>
        </div>

        {tab === "suggested" && <SuggestedTab />}
        {tab === "users" && <UsersTab />}
        {tab === "players" && <PlayersTab />}
        {tab === "data" && <DataTab />}
      </div>
    </div>
  );
}

/* ── Suggested players tab ────────────────────────────────────────── */

function SuggestedTab() {
  const [suggested, setSuggested] = useState<AdminSuggestedPlayer[]>([]);
  const [allPlayers, setAllPlayers] = useState<Player[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [msg, setMsg] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([
      adminGetSuggested(),
      fetchPlayers({ nationality: "England", limit: 600 }),
    ])
      .then(([s, p]) => {
        setSuggested(s);
        setAllPlayers(p.players);
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  const suggestedSet = new Set(suggested.map((s) => s.player_id));

  function togglePlayer(player: Player) {
    if (suggestedSet.has(player.player_id)) {
      setSuggested((prev) => prev.filter((s) => s.player_id !== player.player_id));
    } else {
      setSuggested((prev) => [
        ...prev,
        {
          player_id: player.player_id,
          name: player.name,
          position: player.position,
          nationality: player.nationality,
        },
      ]);
    }
  }

  async function handleSave() {
    setMsg(null);
    try {
      await adminSetSuggested(suggested.map((s) => s.player_id));
      setMsg(`Saved ${suggested.length} suggested players to server ✓`);
    } catch {
      setMsg("Failed to save");
    }
  }

  function handleImportFromBrowser() {
    const localIds = loadSuggestedIds();
    if (localIds.length === 0) {
      setMsg("No suggested players found in your browser storage");
      return;
    }
    // Match local IDs against the full player list to build proper objects
    const playerMap = new Map(allPlayers.map((p) => [p.player_id, p]));
    const imported: AdminSuggestedPlayer[] = [];
    for (const id of localIds) {
      if (suggestedSet.has(id)) continue; // already in list
      const p = playerMap.get(id);
      if (p) {
        imported.push({
          player_id: p.player_id,
          name: p.name,
          position: p.position,
          nationality: p.nationality,
        });
      }
    }
    if (imported.length === 0) {
      setMsg("All browser players are already in the list");
      return;
    }
    setSuggested((prev) => [...prev, ...imported]);
    setMsg(`Imported ${imported.length} players from browser — click "Save to server" to persist`);
  }

  const filtered = search.trim()
    ? allPlayers.filter((p) => p.name.toLowerCase().includes(search.toLowerCase()))
    : [];

  if (loading) return <p className="dashboard-info">Loading…</p>;

  return (
    <div className="admin-section">
      <div className="admin-section-header">
        <h2>Suggested Players ({suggested.length})</h2>
        <div className="admin-header-actions">
          <button className="admin-import-btn" onClick={handleImportFromBrowser}>
            Import from browser
          </button>
          <button className="admin-save-btn" onClick={handleSave}>Save to server</button>
        </div>
      </div>
      {msg && <p className="dashboard-success">{msg}</p>}

      {/* Search to add players */}
      <div className="admin-search-box">
        <input
          type="text"
          placeholder="Search players to add/remove…"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
        {filtered.length > 0 && (
          <div className="admin-search-results">
            {filtered.slice(0, 20).map((p) => (
              <div
                key={p.player_id}
                className={`admin-search-row ${suggestedSet.has(p.player_id) ? "in-list" : ""}`}
                onClick={() => togglePlayer(p)}
              >
                <span>{p.name}</span>
                <span className="admin-search-pos">{p.position}</span>
                <span className="admin-search-action">
                  {suggestedSet.has(p.player_id) ? "✕ Remove" : "+ Add"}
                </span>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Current suggested list */}
      <div className="admin-list">
        {suggested.map((s) => (
          <div key={s.player_id} className="admin-list-row">
            <span>{s.name}</span>
            <span className="admin-list-meta">{s.position}</span>
            <button className="admin-remove-btn" onClick={() => togglePlayer(s as unknown as Player)}>
              ✕
            </button>
          </div>
        ))}
        {suggested.length === 0 && (
          <p className="dashboard-info">No suggested players yet. Use the search above to add some.</p>
        )}
      </div>
    </div>
  );
}

/* ── Users tab ────────────────────────────────────────────────────── */

function UsersTab() {
  const { user: currentUser } = useAuth();
  const [users, setUsers] = useState<AdminUser[]>([]);
  const [loading, setLoading] = useState(true);
  const [msg, setMsg] = useState<string | null>(null);
  const [showAddForm, setShowAddForm] = useState(false);
  const [newEmail, setNewEmail] = useState("");
  const [newName, setNewName] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [newRole, setNewRole] = useState("user");
  const [creating, setCreating] = useState(false);

  useEffect(() => {
    adminGetUsers()
      .then(setUsers)
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  async function toggleRole(u: AdminUser) {
    const newRole = u.role === "admin" ? "user" : "admin";
    await adminSetUserRole(u.id, newRole);
    setUsers((prev) =>
      prev.map((usr) => (usr.id === u.id ? { ...usr, role: newRole } : usr))
    );
  }

  async function handleDelete(u: AdminUser) {
    if (!confirm(`Delete user "${u.display_name}" (${u.email})? This cannot be undone.`)) return;
    setMsg(null);
    try {
      await adminDeleteUser(u.id);
      setUsers((prev) => prev.filter((usr) => usr.id !== u.id));
      setMsg(`Deleted user ${u.display_name}`);
    } catch (err) {
      setMsg(err instanceof Error ? err.message : "Failed to delete user");
    }
  }

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault();
    setMsg(null);
    setCreating(true);
    try {
      const created = await adminCreateUser(newEmail, newName, newPassword, newRole);
      setUsers((prev) => [{ ...created, created_at: new Date().toISOString() }, ...prev]);
      setMsg(`Created user ${created.display_name}`);
      setNewEmail("");
      setNewName("");
      setNewPassword("");
      setNewRole("user");
      setShowAddForm(false);
    } catch (err) {
      setMsg(err instanceof Error ? err.message : "Failed to create user");
    } finally {
      setCreating(false);
    }
  }

  if (loading) return <p className="dashboard-info">Loading…</p>;

  return (
    <div className="admin-section">
      <div className="admin-section-header">
        <h2>Users ({users.length})</h2>
        <button className="admin-save-btn" onClick={() => setShowAddForm(!showAddForm)}>
          {showAddForm ? "Cancel" : "+ Add User"}
        </button>
      </div>
      {msg && <p className="dashboard-success">{msg}</p>}

      {showAddForm && (
        <form className="admin-add-form" onSubmit={handleCreate}>
          <input
            type="email"
            placeholder="Email"
            value={newEmail}
            onChange={(e) => setNewEmail(e.target.value)}
            required
          />
          <input
            type="text"
            placeholder="Display name"
            value={newName}
            onChange={(e) => setNewName(e.target.value)}
            required
          />
          <input
            type="password"
            placeholder="Password"
            value={newPassword}
            onChange={(e) => setNewPassword(e.target.value)}
            required
            minLength={6}
          />
          <select value={newRole} onChange={(e) => setNewRole(e.target.value)}>
            <option value="user">User</option>
            <option value="admin">Admin</option>
          </select>
          <button type="submit" className="admin-save-btn" disabled={creating}>
            {creating ? "Creating…" : "Create"}
          </button>
        </form>
      )}

      <div className="admin-list">
        {users.map((u) => (
          <div key={u.id} className="admin-list-row">
            <div>
              <strong>{u.display_name}</strong>
              <span className="admin-list-meta">{u.email}</span>
            </div>
            <div className="admin-list-right">
              <span className={`role-badge ${u.role}`}>{u.role}</span>
              {u.id !== currentUser?.id && (
                <>
                  <button className="admin-role-btn" onClick={() => toggleRole(u)}>
                    {u.role === "admin" ? "Demote" : "Promote"}
                  </button>
                  <button className="admin-delete-btn" onClick={() => handleDelete(u)} title="Delete user">
                    🗑
                  </button>
                </>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

/* ── Players tab ──────────────────────────────────────────────────── */

function PlayersTab() {
  const [search, setSearch] = useState("");
  const [results, setResults] = useState<AdminPlayer[]>([]);
  const [loading, setLoading] = useState(false);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [editData, setEditData] = useState<Partial<AdminPlayer>>({});
  const [msg, setMsg] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  async function handleSearch(e: React.FormEvent) {
    e.preventDefault();
    if (!search.trim()) return;
    setLoading(true);
    setMsg(null);
    try {
      const players = await adminSearchPlayers(search.trim());
      setResults(players);
      if (players.length === 0) setMsg("No players found");
    } catch {
      setMsg("Search failed");
    } finally {
      setLoading(false);
    }
  }

  function startEdit(p: AdminPlayer) {
    setEditingId(p.player_id);
    setEditData({ name: p.name, position: p.position, nationality: p.nationality, date_of_birth: p.date_of_birth });
    setMsg(null);
  }

  function cancelEdit() {
    setEditingId(null);
    setEditData({});
  }

  async function saveEdit(playerId: number) {
    setSaving(true);
    setMsg(null);
    try {
      const updated = await adminUpdatePlayer(playerId, editData);
      setResults((prev) => prev.map((p) => (p.player_id === playerId ? updated : p)));
      setEditingId(null);
      setEditData({});
      setMsg(`Updated ${updated.name} ✓`);
    } catch (err) {
      setMsg(err instanceof Error ? err.message : "Failed to update player");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="admin-section">
      <h2>Edit Player Data</h2>
      <form className="admin-search-box" onSubmit={handleSearch} style={{ display: "flex", gap: "0.5rem" }}>
        <input
          type="text"
          placeholder="Search by player name…"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          style={{ flex: 1 }}
        />
        <button type="submit" className="admin-save-btn" disabled={loading}>
          {loading ? "Searching…" : "Search"}
        </button>
      </form>
      {msg && <p className="dashboard-success">{msg}</p>}

      <div className="admin-list">
        {results.map((p) =>
          editingId === p.player_id ? (
            <div key={p.player_id} className="admin-edit-row">
              <div className="admin-edit-fields">
                <label>
                  Name
                  <input
                    type="text"
                    value={editData.name ?? ""}
                    onChange={(e) => setEditData({ ...editData, name: e.target.value })}
                  />
                </label>
                <label>
                  Position
                  <input
                    type="text"
                    value={editData.position ?? ""}
                    onChange={(e) => setEditData({ ...editData, position: e.target.value })}
                  />
                </label>
                <label>
                  Nationality
                  <input
                    type="text"
                    value={editData.nationality ?? ""}
                    onChange={(e) => setEditData({ ...editData, nationality: e.target.value })}
                  />
                </label>
                <label>
                  Date of Birth
                  <input
                    type="date"
                    value={editData.date_of_birth ?? ""}
                    onChange={(e) => setEditData({ ...editData, date_of_birth: e.target.value })}
                  />
                </label>
              </div>
              <div className="admin-edit-actions">
                <button className="admin-save-btn" onClick={() => saveEdit(p.player_id)} disabled={saving}>
                  {saving ? "Saving…" : "Save"}
                </button>
                <button className="admin-role-btn" onClick={cancelEdit}>Cancel</button>
              </div>
            </div>
          ) : (
            <div key={p.player_id} className="admin-list-row">
              <div>
                <strong>{p.name}</strong>
                <span className="admin-list-meta">{p.position}</span>
                <span className="admin-list-meta">{p.nationality}</span>
                {p.date_of_birth && <span className="admin-list-meta">{p.date_of_birth}</span>}
              </div>
              <button className="admin-role-btn" onClick={() => startEdit(p)}>Edit</button>
            </div>
          )
        )}
      </div>
    </div>
  );
}

/* ── Data tab ─────────────────────────────────────────────────────── */

function DataTab() {
  const [refreshing, setRefreshing] = useState(false);
  const [msg, setMsg] = useState<string | null>(null);

  async function handleRefresh() {
    setRefreshing(true);
    setMsg(null);
    try {
      await refreshData(["PL"]);
      setMsg("Player data refreshed successfully!");
    } catch (err) {
      setMsg(err instanceof Error ? err.message : "Refresh failed");
    } finally {
      setRefreshing(false);
    }
  }

  return (
    <div className="admin-section">
      <h2>Data Management</h2>
      <p className="dashboard-info">
        Reset and refresh player data from football-data.org. This will fetch the latest Premier League squad data.
      </p>
      <button className="admin-save-btn" onClick={handleRefresh} disabled={refreshing}>
        {refreshing ? "Refreshing…" : "Refresh player data"}
      </button>
      {msg && <p className="dashboard-success" style={{ marginTop: "0.75rem" }}>{msg}</p>}
    </div>
  );
}
