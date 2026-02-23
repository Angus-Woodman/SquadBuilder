from __future__ import annotations

from datetime import date
from typing import Any


def _parse_date(value: str | None) -> date | None:
    """Parse YYYY-MM-DD into a date, return None if missing/invalid."""
    if not value or not isinstance(value, str):
        return None
    try:
        yyyy, mm, dd = value.split("-")
        return date(int(yyyy), int(mm), int(dd))
    except (ValueError, TypeError):
        return None


def transform_competition_teams_payload(
    payload: dict[str, Any],
    *,
    competition_code: str,
) -> dict[str, Any]:
    """
    Transform the response from:
      GET /v4/competitions/{league}/teams

    Into normalized structures:
      - teams: list[team]
      - players: list[player] (deduped globally by player_id)
      - team_players: list[{team_id, player_id}] join table rows

    Notes:
    - Some players might appear in multiple squads across competitions or over time.
      We dedupe players by id, and keep the relationship in team_players.
    """
    competition_code = competition_code.strip().upper()

    teams_out: list[dict[str, Any]] = []
    players_by_id: dict[int, dict[str, Any]] = {}
    team_players_out: list[dict[str, int]] = []

    teams = payload.get("teams") or []
    if not isinstance(teams, list):
        raise ValueError("Expected payload['teams'] to be a list")

    for team in teams:
        if not isinstance(team, dict):
            continue

        team_id = team.get("id")
        if not isinstance(team_id, int):
            # skip if no stable ID
            continue

        area = team.get("area") or {}
        coach = team.get("coach") or {}

        team_row: dict[str, Any] = {
            "team_id": team_id,
            "competition_code": competition_code,
            "name": team.get("name"),
            "short_name": team.get("shortName"),
            "tla": team.get("tla"),
            "crest_url": team.get("crest"),
            "website": team.get("website"),
            "founded": team.get("founded"),
            "club_colors": team.get("clubColors"),
            "venue": team.get("venue"),
            "area_id": area.get("id"),
            "area_name": area.get("name"),
            "area_code": area.get("code"),
            "last_updated": team.get("lastUpdated"),
            # Coach (optional)
            "coach_id": coach.get("id"),
            "coach_name": coach.get("name"),
            "coach_nationality": coach.get("nationality"),
            "coach_date_of_birth": coach.get("dateOfBirth"),  # keep string for now
            "coach_contract_start": (coach.get("contract") or {}).get("start"),
            "coach_contract_until": (coach.get("contract") or {}).get("until"),
        }
        teams_out.append(team_row)

        squad = team.get("squad") or []
        if not isinstance(squad, list):
            continue

        for p in squad:
            if not isinstance(p, dict):
                continue

            player_id = p.get("id")
            if not isinstance(player_id, int):
                continue

            # Create or update a global player record
            existing = players_by_id.get(player_id)
            candidate = {
                "player_id": player_id,
                "name": p.get("name"),
                "position": p.get("position"),
                "nationality": p.get("nationality"),
                "date_of_birth": _parse_date(p.get("dateOfBirth")),
            }

            # If we already saw the player, keep the first non-null values (very simple merge)
            if existing is None:
                players_by_id[player_id] = candidate
            else:
                for k, v in candidate.items():
                    if existing.get(k) in (None, "", []):
                        existing[k] = v

            # Relationship row (team <-> player)
            team_players_out.append({"team_id": team_id, "player_id": player_id})

    players_out = list(players_by_id.values())

    return {
        "competition_code": competition_code,
        "teams": teams_out,
        "players": players_out,
        "team_players": team_players_out,
        "counts": {
            "teams": len(teams_out),
            "players": len(players_out),
            "team_players": len(team_players_out),
        },
    }


def transform_many_competitions(
    payloads_by_competition: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    """
    Transform multiple competition payloads (e.g. {"PL": {...}, "SA": {...}}) and combine.
    """
    all_teams: list[dict[str, Any]] = []
    players_by_id: dict[int, dict[str, Any]] = {}
    all_team_players: list[dict[str, int]] = []

    for comp, payload in payloads_by_competition.items():
        out = transform_competition_teams_payload(payload, competition_code=comp)

        all_teams.extend(out["teams"])
        all_team_players.extend(out["team_players"])

        for p in out["players"]:
            pid = p["player_id"]
            if pid not in players_by_id:
                players_by_id[pid] = p

    return {
        "teams": all_teams,
        "players": list(players_by_id.values()),
        "team_players": all_team_players,
        "counts": {
            "teams": len(all_teams),
            "players": len(players_by_id),
            "team_players": len(all_team_players),
        },
    }
