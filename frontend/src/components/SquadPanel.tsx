import type { Player } from "../types/player";
import { GROUP_LABELS, type PositionGroup, positionGroup } from "../utils/positions";

export function SquadPanel(props: {
  squad: Player[];
  onRemove: (playerId: number) => void;
  maxSize?: number;
}) {
  const max = props.maxSize ?? 26;

  const grouped: Record<PositionGroup, Player[]> = {
    GK: [],
    DEF: [],
    MID: [],
    FWD: [],
    OTHER: [],
  };

  for (const p of props.squad) grouped[positionGroup(p.position)].push(p);

  const groupOrder: PositionGroup[] = ["GK", "DEF", "MID", "FWD", "OTHER"];

  return (
    <div style={{ border: "1px solid #ddd", borderRadius: 10, padding: 14 }}>
      <div style={{ display: "flex", alignItems: "baseline", gap: 10, marginBottom: 10 }}>
        <h2 style={{ margin: 0, fontSize: 18 }}>Selected squad</h2>
        <div style={{ opacity: 0.75 }}>
          {props.squad.length}/{max}
        </div>
      </div>

      {props.squad.length === 0 ? (
        <div style={{ opacity: 0.8 }}>No players selected yet.</div>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
          {groupOrder.map((g) => (
            <div key={g}>
              <div style={{ fontWeight: 600, marginBottom: 6 }}>
                {GROUP_LABELS[g]} <span style={{ opacity: 0.7 }}>({grouped[g].length})</span>
              </div>
              {grouped[g].length === 0 ? (
                <div style={{ opacity: 0.7 }}>—</div>
              ) : (
                <ul style={{ listStyle: "none", padding: 0, margin: 0, display: "flex", flexDirection: "column", gap: 6 }}>
                  {grouped[g]
                    .slice()
                    .sort((a, b) => a.name.localeCompare(b.name))
                    .map((p) => (
                      <li
                        key={p.player_id}
                        style={{
                          display: "flex",
                          justifyContent: "space-between",
                          alignItems: "center",
                          gap: 10,
                          border: "1px solid #eee",
                          borderRadius: 8,
                          padding: "8px 10px",
                        }}
                      >
                        <div style={{ minWidth: 0 }}>
                          <div style={{ fontWeight: 500, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                            {p.name}
                          </div>
                          <div style={{ opacity: 0.75, fontSize: 12 }}>
                            {p.position ?? "—"} • {p.nationality ?? "—"}
                          </div>
                        </div>
                        <button
                          onClick={() => props.onRemove(p.player_id)}
                          style={{ padding: "6px 10px", cursor: "pointer" }}
                        >
                          Remove
                        </button>
                      </li>
                    ))}
                </ul>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
