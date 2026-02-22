import type { PositionGroup } from "../utils/positions";

export function PlayerFilters(props: {
  search: string;
  setSearch: (v: string) => void;
  posFilter: PositionGroup | "ALL";
  setPosFilter: (v: PositionGroup | "ALL") => void;
  loading: boolean;
  playerCount: number;
}) {
  return (
    <div className="filters-bar">
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

      <div className="player-count">
        {props.loading ? "Loading…" : `${props.playerCount} players`}
      </div>
    </div>
  );
}
