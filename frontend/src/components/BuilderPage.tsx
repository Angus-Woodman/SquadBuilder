import { useEffect, useMemo, useRef, useState } from "react";

import { fetchPlayers } from "../api/client";
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
import "./Builder.css";

export function BuilderPage() {
  // Filters
  const [search, setSearch] = useState("");
  const [posFilter, setPosFilter] = useState<PositionGroup | "ALL">("ALL");

  // Data
  const [allPlayers, setAllPlayers] = useState<Player[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Squad selection
  const [selectedIds, setSelectedIds] = useState<number[]>(() => loadSelectedIds());
  const selectedIdSet = useMemo(() => new Set(selectedIds), [selectedIds]);

  // Suggested list
  const [suggestedIds, setSuggestedIds] = useState<number[]>(() => loadSuggestedIds());
  const suggestedIdSet = useMemo(() => new Set(suggestedIds), [suggestedIds]);

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
      const res = await fetchPlayers({ nationality: "England", limit: 600 }, controller.signal);
      setAllPlayers(res.players);

      // Auto-seed suggested list on first load if empty
      if (suggestedIds.length === 0 && res.players.length > 0) {
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

  return (
    <div className="builder">
      <nav className="builder-nav">
        <h1>⚽ Squad Selector</h1>
        <span className="squad-count">26-player World Cup squad</span>
      </nav>

      <div className="builder-body">
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
          </aside>
        </div>
      </div>
    </div>
  );
}
