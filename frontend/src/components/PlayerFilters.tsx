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
    <div className="filters-bar">
      <div className="filter-group">
        <label>Nationality</label>
        <input
          value={props.nationality}
          onChange={(e) => props.setNationality(e.target.value)}
          placeholder="e.g. England"
          style={{ minWidth: 180 }}
        />
      </div>

      <div className="filter-group">
        <label>Search</label>
        <input
          value={props.search}
          onChange={(e) => props.setSearch(e.target.value)}
          placeholder="Search player name"
          style={{ minWidth: 220 }}
        />
      </div>

      <div className="filter-group">
        <label>Position</label>
        <select
          value={props.posFilter}
          onChange={(e) => props.setPosFilter(e.target.value as PositionGroup | "ALL")}
          style={{ minWidth: 130 }}
        >
          <option value="ALL">All</option>
          <option value="GK">GK</option>
          <option value="DEF">DEF</option>
          <option value="MID">MID</option>
          <option value="FWD">FWD</option>
          <option value="OTHER">Other</option>
        </select>
      </div>

      <div className="filter-group">
        <label>Limit</label>
        <input
          type="number"
          min={1}
          max={2000}
          value={props.limit}
          onChange={(e) => props.setLimit(Math.max(1, Math.min(2000, Number(e.target.value) || 1)))}
        />
      </div>

      <button
        className="refresh-btn"
        onClick={props.onRefresh}
        disabled={props.refreshing}
      >
        {props.refreshing ? "Refreshing…" : "↻ Refresh data"}
      </button>

      <div className="player-count">
        {props.loading ? "Loading…" : `${props.playerCount} players`}
      </div>
    </div>
  );
}
