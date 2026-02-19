import type { Player } from "../types/player";

export type PositionGroup = "GK" | "DEF" | "MID" | "FWD" | "OTHER";

export function positionGroup(position: Player["position"]): PositionGroup {
  const p = (position ?? "").toLowerCase();

  // football-data.org can return both broad + specific positions
  if (p.includes("goal")) return "GK";

  // defenders
  if (
    p.includes("back") ||
    p.includes("defence") ||
    p.includes("defender") ||
    p.includes("centre-back") ||
    p.includes("center-back") ||
    p.includes("full-back") ||
    p.includes("wing-back")
  )
    return "DEF";

  // midfield
  if (p.includes("midfield") || p.includes("midfielder")) return "MID";

  // forwards
  if (
    p.includes("forward") ||
    p.includes("offence") ||
    p.includes("offense") ||
    p.includes("winger") ||
    p.includes("striker")
  )
    return "FWD";

  return "OTHER";
}

export const GROUP_LABELS: Record<PositionGroup, string> = {
  GK: "Goalkeepers",
  DEF: "Defenders",
  MID: "Midfielders",
  FWD: "Forwards",
  OTHER: "Other",
};
