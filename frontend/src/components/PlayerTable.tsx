import type { Player } from "../types/player";
import { positionGroup } from "../utils/positions";

export function PlayerTable(props: {
  players: Player[];
  selectedIds: Set<number>;
  onAdd: (p: Player) => void;
  disabledAdd?: boolean;
}) {
  return (
    <div style={{ overflowX: "auto", border: "1px solid #ddd", borderRadius: 10 }}>
      <table style={{ width: "100%", borderCollapse: "collapse" }}>
        <thead>
          <tr style={{ background: "#f7f7f7" }}>
            <th style={th}>Add</th>
            <th style={th}>Name</th>
            <th style={th}>Group</th>
            <th style={th}>Position</th>
            <th style={th}>Nationality</th>
            <th style={th}>DOB</th>
          </tr>
        </thead>
        <tbody>
          {props.players.map((p) => {
            const already = props.selectedIds.has(p.player_id);
            return (
              <tr key={p.player_id}>
                <td style={td}>
                  <button
                    onClick={() => props.onAdd(p)}
                    disabled={already || props.disabledAdd}
                    style={{ padding: "6px 10px", cursor: already ? "not-allowed" : "pointer" }}
                    title={already ? "Already selected" : "Add to squad"}
                  >
                    {already ? "✓" : "+"}
                  </button>
                </td>
                <td style={td}>{p.name}</td>
                <td style={td}>{positionGroup(p.position)}</td>
                <td style={td}>{p.position ?? "—"}</td>
                <td style={td}>{p.nationality ?? "—"}</td>
                <td style={td}>{p.date_of_birth ?? "—"}</td>
              </tr>
            );
          })}
          {props.players.length === 0 && (
            <tr>
              <td style={td} colSpan={6}>
                No players found.
              </td>
            </tr>
          )}
        </tbody>
      </table>
    </div>
  );
}

const th: React.CSSProperties = {
  textAlign: "left",
  padding: "10px 12px",
  borderBottom: "1px solid #ddd",
  fontWeight: 600,
};

const td: React.CSSProperties = {
  padding: "10px 12px",
  borderBottom: "1px solid #eee",
  whiteSpace: "nowrap",
};
