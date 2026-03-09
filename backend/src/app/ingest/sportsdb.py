"""Enrich players with data from TheSportsDB lookup endpoint.

The search endpoint returns basic info + an ``idPlayer`` which can then
be used with the lookup endpoint to get detailed fields:

    Search:  GET /searchplayers.php?p=Harry_Kane  → idPlayer
    Lookup:  GET /lookupplayer.php?id=<idPlayer>   → strSide, strPosition, …

Fields available from lookup:
    strSide          – preferred foot ("Right", "Left", "Both")
    strPosition      – primary position
    strHeight        – height string
    strWeight        – weight string
    strTeam          – current team name
    strNumber        – shirt number
    strDescriptionEN – player biography

Rate limit: 30 requests/minute on the free tier (API key "3").
Since we need 2 API calls per player (search + lookup), we space them
accordingly.
"""

from __future__ import annotations

import time
from typing import Any

import requests

_API_KEY = "3"
_SPORTSDB_SEARCH = f"https://www.thesportsdb.com/api/v1/json/{_API_KEY}/searchplayers.php"
_SPORTSDB_LOOKUP = f"https://www.thesportsdb.com/api/v1/json/{_API_KEY}/lookupplayer.php"

# Characters that TheSportsDB search cannot handle
_SEARCH_STRIP_CHARS = str.maketrans("", "", "'''`")


def _request_with_retry(
    url: str,
    params: dict[str, str],
    *,
    max_retries: int = 3,
    timeout: int = 10,
) -> dict[str, Any] | None:
    """GET with retry on 429 / 5xx."""
    for attempt in range(max_retries):
        try:
            resp = requests.get(url, params=params, timeout=timeout)
            if resp.status_code == 429 or resp.status_code >= 500:
                wait = 2 ** (attempt + 1)
                time.sleep(wait)
                continue
            resp.raise_for_status()
            return resp.json()
        except (requests.RequestException, ValueError):
            return None
    return None


def _search_player_id(
    name: str,
    *,
    date_of_birth: str | None = None,
    club: str | None = None,
) -> str | None:
    """Search TheSportsDB for a soccer player and return their idPlayer.

    When multiple soccer players share the same name, use ``date_of_birth``
    (ISO format) and/or ``club`` to pick the right one.
    """
    data = _request_with_retry(_SPORTSDB_SEARCH, {"p": name})
    if not data:
        return None

    result = _pick_best_match(data.get("player") or [], date_of_birth=date_of_birth, club=club)
    if result:
        return result

    # Retry with apostrophes stripped
    cleaned = name.translate(_SEARCH_STRIP_CHARS)
    if cleaned != name:
        data = _request_with_retry(_SPORTSDB_SEARCH, {"p": cleaned})
        if data:
            result = _pick_best_match(
                data.get("player") or [],
                date_of_birth=date_of_birth,
                club=club,
            )
            if result:
                return result

    return None


def _pick_best_match(
    players: list[Any],
    *,
    date_of_birth: str | None = None,
    club: str | None = None,
) -> str | None:
    """Pick the best soccer match from a TheSportsDB search result list.

    Scoring: +2 for DOB match, +1 for club substring match.
    Falls back to first soccer player when no hints are provided.
    """
    soccer = [
        p for p in players if isinstance(p, dict) and (p.get("strSport") or "").lower() == "soccer"
    ]
    if not soccer:
        return None

    # If we have nothing to disambiguate with, return first
    if not date_of_birth and not club:
        return soccer[0].get("idPlayer")

    best_id: str | None = None
    best_score = -1

    club_lower = (club or "").lower()

    for p in soccer:
        score = 0
        if date_of_birth and (p.get("dateBorn") or "") == date_of_birth:
            score += 2
        if club_lower:
            team = (p.get("strTeam") or "").lower()
            if club_lower in team or team in club_lower:
                score += 1
        if score > best_score:
            best_score = score
            best_id = p.get("idPlayer")

    return best_id


def lookup_player(player_id: str) -> dict[str, Any] | None:
    """Lookup full player details by TheSportsDB player ID.

    Returns the raw player dict or None.
    """
    data = _request_with_retry(_SPORTSDB_LOOKUP, {"id": player_id})
    if not data:
        return None

    players = data.get("players") or []
    if players and isinstance(players[0], dict):
        return players[0]

    return None


def fetch_player_details(
    name: str,
    *,
    date_of_birth: str | None = None,
    club: str | None = None,
) -> dict[str, Any] | None:
    """Search + lookup pipeline: returns full TheSportsDB player record.

    Two API calls: search by name → lookup by ID.
    ``date_of_birth`` (ISO) and ``club`` are used for disambiguation
    when multiple players share the same name.
    Returns None if player not found.
    """
    player_id = _search_player_id(name, date_of_birth=date_of_birth, club=club)
    if not player_id:
        return None

    return lookup_player(player_id)


def enrich_from_sportsdb(
    players: list[dict[str, Any]],
    *,
    delay: float = 2.0,
    on_progress: callable | None = None,
) -> int:
    """Enrich player dicts with data from TheSportsDB lookup.

    Adds/updates in-place:
        - preferred_foot  (from strSide)
        - photo_url       (from strCutout or strThumb, if missing)
        - club            (from strTeam, if missing)

    Parameters
    ----------
    players:
        List of player dicts (must have ``"name"``).  Modified in-place.
    delay:
        Seconds between API call pairs to stay under rate limit.
    on_progress:
        Optional callback ``(index, total, name)`` for progress reporting.

    Returns the number of players for which any data was found.
    """
    found = 0
    total = len(players)

    for i, player in enumerate(players):
        name = player.get("name")
        if not name:
            continue

        details = fetch_player_details(
            name,
            date_of_birth=player.get("date_of_birth"),
            club=player.get("club"),
        )
        if details:
            enriched = False

            # Preferred foot
            side = details.get("strSide")
            if side and side.strip():
                player["preferred_foot"] = side.strip()
                enriched = True

            # Photo (only if player doesn't already have one)
            if not player.get("photo_url"):
                photo = details.get("strCutout") or details.get("strThumb")
                if photo:
                    player["photo_url"] = photo
                    enriched = True

            # Club (only if player doesn't already have one)
            if not player.get("club"):
                team = details.get("strTeam")
                if team and team.strip():
                    player["club"] = team.strip()
                    enriched = True

            if enriched:
                found += 1

        if on_progress:
            on_progress(i + 1, total, name)

        # Two API calls per player; 30 req/min free tier → ~4s between players
        if i < total - 1:
            time.sleep(delay)

    return found
