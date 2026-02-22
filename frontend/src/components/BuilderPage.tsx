import { useEffect, useMemo, useRef, useState } from "react";
import { Link, useLocation } from "react-router-dom";

import { fetchPlayers, fetchSuggestedIds, createSquad, updateSquad } from "../api/client";
import { useAuth } from "../context/AuthContext";
import { PlayerFilters } from "./PlayerFilters";
import { PlayerTable } from "./PlayerTable";
import { SquadPanel } from "./SquadPanel";
import type { Player } from "../types/player";
import {
  loadSelectedIds,
  saveSelectedIds,
  loadSuggestedIds,
  saveSuggestedIds,
} from "../utils/storage";
import type { PositionGroup } from "../utils/positions";
import { positionGroup } from "../utils/positions";
import "./Dashboard.css";
import "./Builder.css";

export function BuilderPage() {
  const { user, logout } = useAuth();
  const location = useLocation();
  const navState = location.state as { editSquadId?: number; editPlayerIds?: number[]; editSquadName?: string } | null;

  // Filters
  const [search, setSearch] = useState("");
  const [posFilter, setPosFilter] = useState<PositionGroup | "ALL">("ALL");

  // Data
  const [allPlayers, setAllPlayers] = useState<Player[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Squad selection — pre-load from navigation state if editing a saved squad
  const [selectedIds, setSelectedIds] = useState<number[]>(() =>
    navState?.editPlayerIds ?? loadSelectedIds()
  );
  const selectedIdSet = useMemo(() => new Set(selectedIds), [selectedIds]);

  // Suggested list
  const [suggestedIds, setSuggestedIds] = useState<number[]>(() => loadSuggestedIds());
  const suggestedIdSet = useMemo(() => new Set(suggestedIds), [suggestedIds]);

  // Save squad
  const [saveName, setSaveName] = useState(navState?.editSquadName ?? "");
  const [saveMsg, setSaveMsg] = useState<string | null>(null);
  const [editingSquadId] = useState<number | null>(navState?.editSquadId ?? null);

  const abortRef = useRef<AbortController | null>(null);

  const filteredPlayers = useMemo(() => {
    const s = search.trim().toLowerCase();
    return allPlayers.filter((p) => {
      if (posFilter !== "ALL" && positionGroup(p.position) !== posFilter) return false;
      if (s && !p.name.toLowerCase().includes(s)) return false;
      return true;
    });
  }, [allPlayers, search, posFilter]);

  const squad = useMemo(
    () => allPlayers.filter((p) => selectedIdSet.has(p.player_id)),
    [allPlayers, selectedIdSet]
  );

  async function load() {
    abortRef.current?.abort();
    const controller = new AbortController();
    abortRef.current = controller;

    setLoading(true);
    setError(null);
    try {
      const [res, serverSuggested] = await Promise.all([
        fetchPlayers({ nationality: "England", limit: 600 }, controller.signal),
        fetchSuggestedIds(),
      ]);
      setAllPlayers(res.players);

      // Use server-side suggested list if available, else fallback to local/seed
      if (serverSuggested.length > 0) {
        setSuggestedIds(serverSuggested);
        saveSuggestedIds(serverSuggested);
      } else if (suggestedIds.length === 0 && res.players.length > 0) {
        // Auto-seed suggested list on first load if empty
        const seed = res.players.map((p) => p.player_id);
        setSuggestedIds(seed);
        saveSuggestedIds(seed);
      }
    } catch (e) {
      if (e instanceof DOMException && e.name === "AbortError") return;
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setLoading(false);
    }
  }

  function addToSquad(p: Player) {
    setSelectedIds((prev) => {
      if (prev.length >= 26) return prev;
      if (prev.includes(p.player_id)) return prev;
      const next = [...prev, p.player_id];
      saveSelectedIds(next);
      return next;
    });
  }

  function removeFromSquad(playerId: number) {
    setSelectedIds((prev) => {
      const next = prev.filter((id) => id !== playerId);
      saveSelectedIds(next);
      return next;
    });
  }

  function toggleSuggested(playerId: number) {
    setSuggestedIds((prev) => {
      const next = prev.includes(playerId)
        ? prev.filter((id) => id !== playerId)
        : [...prev, playerId];
      saveSuggestedIds(next);
      return next;
    });
  }

  useEffect(() => {
    void load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function handleSaveSquad() {
    if (!user) return;
    if (!saveName.trim()) {
      setSaveMsg("Enter a squad name first");
      return;
    }
    if (selectedIds.length === 0) {
      setSaveMsg("Select some players first");
      return;
    }
    try {
      if (editingSquadId) {
        await updateSquad(editingSquadId, saveName.trim(), selectedIds);
        setSaveMsg("Squad updated!");
      } else {
        await createSquad(saveName.trim(), selectedIds);
        setSaveMsg("Squad saved!");
      }
      if (!editingSquadId) setSaveName("");
    } catch (err) {
      setSaveMsg(err instanceof Error ? err.message : "Save failed");
    }
  }

  return (
    <div className="dashboard-page">
      <nav className="dashboard-nav">
        <Link to="/" className="dashboard-brand">⚽ Squad Builder</Link>
        <div className="dashboard-nav-links">
          <Link to="/builder" className="active">Builder</Link>
          {user && (
            <>
              <Link to="/squads">My Squads</Link>
              <Link to="/friends">Friends</Link>
              {user.role === "admin" && <Link to="/admin">Admin</Link>}
              <span className="dashboard-user">{user.display_name}</span>
              <button className="dashboard-logout" onClick={logout}>Log out</button>
            </>
          )}
          {!user && <Link to="/login">Log in</Link>}
        </div>
      </nav>

      <div className="dashboard-content dashboard-content--wide">
        <PlayerFilters
          search={search}
          setSearch={setSearch}
          posFilter={posFilter}
          setPosFilter={setPosFilter}
          loading={loading}
          playerCount={filteredPlayers.length}
        />

        {error && (
          <div className="error-banner">
            <strong>Error:</strong> {error}
          </div>
        )}

        <div className="builder-grid">
          <section>
            <h2>Player list</h2>
            <PlayerTable
              players={filteredPlayers}
              selectedIds={selectedIdSet}
              suggestedIds={suggestedIdSet}
              onAdd={addToSquad}
              onToggleSuggested={toggleSuggested}
              disabledAdd={selectedIds.length >= 26}
            />
          </section>

          <aside>
            <SquadPanel squad={squad} onRemove={removeFromSquad} maxSize={26} />

            {user && selectedIds.length > 0 && (
              <div className="save-squad-section">
                {editingSquadId && (
                  <p className="save-squad-editing">Editing saved squad</p>
                )}
                <input
                  type="text"
                  placeholder="Squad name…"
                  value={saveName}
                  onChange={(e) => setSaveName(e.target.value)}
                  className="save-squad-input"
                />
                <button className="save-squad-btn" onClick={handleSaveSquad}>
                  {editingSquadId ? "Update squad" : "Save squad"}
                </button>
                {saveMsg && <p className="save-squad-msg">{saveMsg}</p>}
              </div>
            )}
          </aside>
        </div>
      </div>
    </div>
  );
}
