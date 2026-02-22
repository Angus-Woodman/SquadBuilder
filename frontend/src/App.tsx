import { useEffect, useMemo, useRef, useState } from "react";
import "./App.css";

import { fetchPlayers, refreshData } from "./api/client";
import { PlayerFilters } from "./components/PlayerFilters";
import { PlayerTable } from "./components/PlayerTable";
import { SquadPanel } from "./components/SquadPanel";
import type { Player } from "./types/player";
import { loadSelectedIds, saveSelectedIds } from "./utils/storage";
import type { PositionGroup } from "./utils/positions";
import { positionGroup } from "./utils/positions";

export default function App() {
  // Filters
  const [nationality, setNationality] = useState("England");
  const [search, setSearch] = useState("");
  const [posFilter, setPosFilter] = useState<PositionGroup | "ALL">("ALL");
  const [limit, setLimit] = useState(400);

  // Data
  const [allPlayers, setAllPlayers] = useState<Player[]>([]);
  const [loading, setLoading] = useState(false);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Squad selection
  const [selectedIds, setSelectedIds] = useState<number[]>(() => loadSelectedIds());
  const selectedIdSet = useMemo(() => new Set(selectedIds), [selectedIds]);
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
      const res = await fetchPlayers({ nationality, limit }, controller.signal);
      setAllPlayers(res.players);
    } catch (e) {
      if (e instanceof DOMException && e.name === "AbortError") return;
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setLoading(false);
    }
  }

  async function onRefresh() {
    setRefreshing(true);
    setError(null);
    try {
      // defaulting to PL for now; you can extend to a competition picker later
      await refreshData(["PL"]);
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setRefreshing(false);
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

  useEffect(() => {
    void load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [nationality, limit]);

  return (
    <div style={{ maxWidth: 1200, margin: "0 auto", padding: 24 }}>
      <header style={{ display: "flex", alignItems: "baseline", justifyContent: "space-between", gap: 12 }}>
        <h1 style={{ margin: 0 }}>England World Cup Squad Selector</h1>
        <div style={{ opacity: 0.75 }}>Pretend you’re Thomas Tuchel!</div>
      </header>

      <div style={{ marginTop: 16, marginBottom: 16 }}>
        <PlayerFilters
          nationality={nationality}
          setNationality={setNationality}
          search={search}
          setSearch={setSearch}
          posFilter={posFilter}
          setPosFilter={setPosFilter}
          limit={limit}
          setLimit={setLimit}
          onRefresh={onRefresh}
          refreshing={refreshing}
          loading={loading}
          playerCount={filteredPlayers.length}
        />
      </div>

      {error && (
        <div style={{ background: "#fee", border: "1px solid #f99", padding: 12, borderRadius: 8, marginBottom: 16 }}>
          <strong>Error:</strong> {error}
        </div>
      )}

      <div
        style={{
          display: "grid",
          gridTemplateColumns: "1.6fr 1fr",
          gap: 16,
          alignItems: "start",
        }}
      >
        <section>
          <h2 style={{ marginTop: 0, fontSize: 18 }}>Player list</h2>
          <PlayerTable players={filteredPlayers} selectedIds={selectedIdSet} onAdd={addToSquad} disabledAdd={selectedIds.length >= 26} />
        </section>

        <aside>
          <SquadPanel squad={squad} onRemove={removeFromSquad} maxSize={26} />
        </aside>
      </div>
    </div>
  );
}
