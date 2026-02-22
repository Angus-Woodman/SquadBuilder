import type { Player } from "../types/player";
import { positionGroup } from "../utils/positions";

export function PlayerTable(props: {
  players: Player[];
  selectedIds: Set<number>;
  onAdd: (p: Player) => void;
  disabledAdd?: boolean;
}) {
  return (
    <div className="player-table-wrap">
      <table className="player-table">
        <thead>
          <tr>
            <th></th>
            <th>Name</th>
            <th>Group</th>
            <th>Position</th>
            <th>Nationality</th>
            <th>DOB</th>
          </tr>
        </thead>
        <tbody>
          {props.players.map((p) => {
            const already = props.selectedIds.has(p.player_id);
            return (
              <tr key={p.player_id}>
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
                <td>{positionGroup(p.position)}</td>
                <td>{p.position ?? "—"}</td>
                <td>{p.nationality ?? "—"}</td>
                <td>{p.date_of_birth ?? "—"}</td>
              </tr>
            );
          })}
          {props.players.length === 0 && (
            <tr>
              <td className="no-players-row" colSpan={6}>
                No players found.
              </td>
            </tr>
          )}
        </tbody>
      </table>
    </div>
  );
}
