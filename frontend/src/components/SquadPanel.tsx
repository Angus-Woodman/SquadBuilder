import { useState } from "react";
import type { Player } from "../types/player";
import { GROUP_LABELS, type PositionGroup, positionGroup } from "../utils/positions";
import { PlayerProfile } from "./PlayerProfile";

export function SquadPanel(props: {
  squad: Player[];
  onRemove: (playerId: number) => void;
  maxSize?: number;
}) {
  const max = props.maxSize ?? 26;
  const [profilePlayer, setProfilePlayer] = useState<Player | null>(null);

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
    <div className="squad-panel">
      <div className="squad-header">
        <h2>Selected squad</h2>
        <span className="count">
          {props.squad.length}/{max}
        </span>
      </div>

      {props.squad.length === 0 ? (
        <div className="squad-empty">No players selected yet.</div>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
          {groupOrder.map((g) => (
            <div key={g}>
              <div className="squad-group-label">
                {GROUP_LABELS[g]} <span>({grouped[g].length})</span>
              </div>
              {grouped[g].length === 0 ? (
                <div style={{ opacity: 0.35 }}>—</div>
              ) : (
                <ul style={{ listStyle: "none", padding: 0, margin: 0, display: "flex", flexDirection: "column", gap: 6 }}>
                  {grouped[g]
                    .slice()
                    .sort((a, b) => a.name.localeCompare(b.name))
                    .map((p) => (
                      <li key={p.player_id} className="squad-player">
                        <div style={{ minWidth: 0 }}>
                          <div
                            className="squad-player-name player-name-clickable"
                            onClick={() => setProfilePlayer(p)}
                          >
                            {p.name}
                          </div>
                          <div className="squad-player-meta">
                            {p.position ?? "—"} · {p.nationality ?? "—"}
                          </div>
                        </div>
                        <button
                          className="remove-btn"
                          onClick={() => props.onRemove(p.player_id)}
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

      {profilePlayer && (
        <PlayerProfile
          player={profilePlayer}
          onClose={() => setProfilePlayer(null)}
        />
      )}
    </div>
  );
}
