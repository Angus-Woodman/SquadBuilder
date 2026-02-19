import type { PositionGroup } from "../utils/positions";

export function PlayerFilters(props: {
  nationality: string;
  setNationality: (v: string) => void;
  search: string;
  setSearch: (v: string) => void;
  posFilter: PositionGroup | "ALL";
  setPosFilter: (v: PositionGroup | "ALL") => void;
  limit: number;
  setLimit: (n: number) => void;
  onRefresh: () => void;
  refreshing: boolean;
  loading: boolean;
  playerCount: number;
}) {
  return (
    <div style={{ display: "flex", gap: 12, flexWrap: "wrap", alignItems: "end" }}>
      <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
        <label>Nationality</label>
        <input
          value={props.nationality}
          onChange={(e) => props.setNationality(e.target.value)}
          placeholder="e.g. England"
          style={{ padding: "8px 10px", minWidth: 200 }}
        />
      </div>

      <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
        <label>Search</label>
        <input
          value={props.search}
          onChange={(e) => props.setSearch(e.target.value)}
          placeholder="Search player name"
          style={{ padding: "8px 10px", minWidth: 240 }}
        />
      </div>

      <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
        <label>Position</label>
        <select
          value={props.posFilter}
          onChange={(e) => props.setPosFilter(e.target.value as any)}
          style={{ padding: "8px 10px", minWidth: 150 }}
        >
          <option value="ALL">All</option>
          <option value="GK">GK</option>
          <option value="DEF">DEF</option>
          <option value="MID">MID</option>
          <option value="FWD">FWD</option>
          <option value="OTHER">Other</option>
        </select>
      </div>

      <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
        <label>Limit</label>
        <input
          type="number"
          min={1}
          max={2000}
          value={props.limit}
          onChange={(e) => props.setLimit(Math.max(1, Math.min(2000, Number(e.target.value) || 1)))}
          style={{ padding: "8px 10px", width: 110 }}
        />
      </div>

      <button
        onClick={props.onRefresh}
        disabled={props.refreshing}
        style={{ padding: "10px 14px", cursor: props.refreshing ? "not-allowed" : "pointer" }}
      >
        {props.refreshing ? "Refreshing..." : "Refresh data"}
      </button>

      <div style={{ marginLeft: "auto", opacity: 0.8 }}>
        {props.loading ? "Loading..." : `${props.playerCount} players`}
      </div>
    </div>
  );
}
