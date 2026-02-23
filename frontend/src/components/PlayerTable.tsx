import { useState } from "react";
import type { Player } from "../types/player";
import {
  GROUP_LABELS,
  type PositionGroup,
  positionGroup,
} from "../utils/positions";

export function PlayerTable(props: {
  players: Player[];
  selectedIds: Set<number>;
  suggestedIds: Set<number>;
  onAdd: (p: Player) => void;
  onToggleSuggested: (playerId: number) => void;
  disabledAdd?: boolean;
}) {
  const groupOrder: PositionGroup[] = ["GK", "DEF", "MID", "FWD", "OTHER"];

  // Group players by position
  const grouped: Record<PositionGroup, Player[]> = {
    GK: [],
    DEF: [],
    MID: [],
    FWD: [],
    OTHER: [],
  };
  for (const p of props.players) {
    grouped[positionGroup(p.position)].push(p);
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
      {groupOrder.map((g) => {
        const all = grouped[g];
        if (all.length === 0) return null;

        const suggested = all.filter((p) => props.suggestedIds.has(p.player_id));
        const rest = all.filter((p) => !props.suggestedIds.has(p.player_id));

        return (
          <PositionSection
            key={g}
            group={g}
            suggested={suggested}
            rest={rest}
            selectedIds={props.selectedIds}
            suggestedIds={props.suggestedIds}
            onAdd={props.onAdd}
            onToggleSuggested={props.onToggleSuggested}
            disabledAdd={props.disabledAdd}
          />
        );
      })}
    </div>
  );
}

function PositionSection(props: {
  group: PositionGroup;
  suggested: Player[];
  rest: Player[];
  selectedIds: Set<number>;
  suggestedIds: Set<number>;
  onAdd: (p: Player) => void;
  onToggleSuggested: (playerId: number) => void;
  disabledAdd?: boolean;
}) {
  const [expanded, setExpanded] = useState(false);
  const displayPlayers = expanded
    ? [...props.suggested, ...props.rest]
    : props.suggested;

  return (
    <div className="position-section">
      <div className="position-section-header">
        <h3 className="position-section-title">
          {GROUP_LABELS[props.group]}{" "}
          <span className="position-section-count">
            {props.suggested.length} suggested · {props.suggested.length + props.rest.length} total
          </span>
        </h3>
        {props.rest.length > 0 && (
          <button
            className="expand-btn"
            onClick={() => setExpanded((v) => !v)}
          >
            {expanded
              ? "Show suggested only"
              : `Show all ${props.suggested.length + props.rest.length}`}
          </button>
        )}
      </div>

      {displayPlayers.length === 0 ? (
        <div className="no-players-row">
          No suggested players.{" "}
          <button className="expand-btn" onClick={() => setExpanded(true)}>
            Browse all {props.rest.length}
          </button>
        </div>
      ) : (
        <div className="player-table-wrap">
          <table className="player-table">
            <colgroup>
              <col style={{ width: "48px" }} />
              <col style={{ width: "40%" }} />
              <col style={{ width: "25%" }} />
              <col style={{ width: "25%" }} />
              <col style={{ width: "48px" }} />
            </colgroup>
            <thead>
              <tr>
                <th></th>
                <th>Name</th>
                <th>Position</th>
                <th>DOB</th>
                <th
                  className="col-star"
                  title="Add or remove from your suggested list"
                  style={{ visibility: expanded ? "visible" : "hidden" }}
                >
                  ★
                </th>
              </tr>
            </thead>
            <tbody>
              {displayPlayers.map((p) => {
                const already = props.selectedIds.has(p.player_id);
                const isSuggested = props.suggestedIds.has(p.player_id);
                return (
                  <tr key={p.player_id} className={isSuggested ? "" : "row-non-suggested"}>
                    <td>
                      <button
                        className={`add-btn${already ? " selected" : ""}`}
                        onClick={() => props.onAdd(p)}
                        disabled={already || props.disabledAdd}
                        title={already ? "Already selected" : "Add to squad"}
                      >
                        {already ? "✓" : "+"}
                      </button>
                    </td>
                    <td>{p.name}</td>
                    <td>{p.position ?? "—"}</td>
                    <td>{p.date_of_birth ?? "—"}</td>
                    <td className="col-star" style={{ visibility: expanded ? "visible" : "hidden" }}>
                      <button
                        className={`suggest-btn${isSuggested ? " active" : ""}`}
                        onClick={() => props.onToggleSuggested(p.player_id)}
                        disabled={!expanded}
                        title={isSuggested ? "Remove from suggested" : "Add to suggested"}
                      >
                        {isSuggested ? "★" : "☆"}
                      </button>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
