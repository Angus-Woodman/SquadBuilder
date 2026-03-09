"""Fetch current-season club stats from Understat.

Understat exposes a POST endpoint that returns per-player season statistics
for a given league and season.  We query all five top European leagues to
cover England players regardless of where they play.

Endpoint:
    POST https://understat.com/main/getPlayersStats/
    Body: league=EPL&season=2025
    Response: {"success": true, "players": [...]}

Each player object contains:
    id, player_name, games, time (minutes), goals, xG, assists, xA,
    shots, key_passes, yellow_cards, red_cards, position, team_title,
    npg, npxG, xGChain, xGBuildup
"""

from __future__ import annotations

import time
from typing import Any

import requests

_UNDERSTAT_URL = "https://understat.com/main/getPlayersStats/"

# Understat uses the year the season *starts* in (e.g. 2025 → 2025/26)
_CURRENT_SEASON = "2025"

# All leagues Understat covers
ALL_LEAGUES = ["EPL", "La_liga", "Bundesliga", "Serie_A", "Ligue_1"]


def fetch_league_players(
    league: str,
    *,
    season: str = _CURRENT_SEASON,
    timeout: int = 20,
) -> list[dict[str, Any]]:
    """Fetch all player stats for a league/season from Understat.

    Returns a list of raw player dicts as returned by the API.
    """
    resp = requests.post(
        _UNDERSTAT_URL,
        data={"league": league, "season": season},
        headers={"Accept-Encoding": "gzip, deflate"},
        timeout=timeout,
    )
    resp.raise_for_status()

    data = resp.json()
    if not data.get("success"):
        return []

    return data.get("players", [])


def fetch_all_leagues(
    *,
    leagues: list[str] | None = None,
    season: str = _CURRENT_SEASON,
    delay: float = 1.0,
    on_progress: callable | None = None,
) -> list[dict[str, Any]]:
    """Fetch player stats across multiple leagues.

    Players who transferred mid-season may appear in multiple leagues;
    we keep ALL entries (later matching picks the best one or combines).

    Returns a flat list of player dicts with an added ``_league`` key.
    """
    if leagues is None:
        leagues = list(ALL_LEAGUES)

    all_players: list[dict[str, Any]] = []

    for i, league in enumerate(leagues):
        players = fetch_league_players(league, season=season)
        for p in players:
            p["_league"] = league
        all_players.extend(players)

        if on_progress:
            on_progress(i + 1, len(leagues), league, len(players))

        if i < len(leagues) - 1:
            time.sleep(delay)

    return all_players


def _normalise_name(name: str) -> str:
    """Lowercase and strip accents/diacritics for fuzzy matching."""
    import unicodedata

    nfkd = unicodedata.normalize("NFKD", name)
    stripped = "".join(c for c in nfkd if not unicodedata.combining(c))
    return stripped.lower().strip()


def match_players(
    understat_players: list[dict[str, Any]],
    db_players: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Match Understat stats to existing DB players by name.

    When a DB player matches multiple Understat entries (e.g. mid-season
    transfer), we pick the one with more minutes played.

    Returns a list of dicts ready for ``update_player_season_stats``.
    """
    from collections import defaultdict

    # Build Understat lookup: normalised name → list of entries
    us_index: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for p in understat_players:
        key = _normalise_name(p.get("player_name", ""))
        if key:
            us_index[key].append(p)

    matched: list[dict[str, Any]] = []

    for db_p in db_players:
        db_name = _normalise_name(db_p.get("name", ""))
        if not db_name:
            continue

        candidates = us_index.get(db_name, [])
        if not candidates:
            continue

        # Pick the entry with the most minutes
        best = max(candidates, key=lambda c: int(c.get("time", "0") or "0"))

        result: dict[str, Any] = {
            "player_id": db_p["player_id"],
            "season_games": int(best.get("games", "0") or "0"),
            "season_minutes": int(best.get("time", "0") or "0"),
            "season_goals": int(best.get("goals", "0") or "0"),
            "season_assists": int(best.get("assists", "0") or "0"),
            "season_xg": best.get("xG"),
            "season_xa": best.get("xA"),
            "season_yellow_cards": int(best.get("yellow_cards", "0") or "0"),
            "season_red_cards": int(best.get("red_cards", "0") or "0"),
            "season_key_passes": int(best.get("key_passes", "0") or "0"),
            "season_shots": int(best.get("shots", "0") or "0"),
        }

        # Fill in missing club from Understat's team_title
        if not db_p.get("club") and best.get("team_title"):
            result["club"] = best["team_title"]

        matched.append(result)

    return matched
