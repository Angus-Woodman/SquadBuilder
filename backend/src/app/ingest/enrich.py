"""Enrich player data from free third-party sources.

Currently supports:
- Player photos from TheSportsDB (free, no API key required)
"""

from __future__ import annotations

import time
from typing import Any

import requests

_SPORTSDB_SEARCH = "https://www.thesportsdb.com/api/v1/json/3/searchplayers.php"

# Characters that TheSportsDB search cannot handle — stripped for retry
_SEARCH_STRIP_CHARS = str.maketrans("", "", "'''`")


def _search_sportsdb(query: str, *, max_retries: int = 3) -> str | None:
    """Low-level search against TheSportsDB, with retry on 429 / 5xx."""
    for attempt in range(max_retries):
        try:
            resp = requests.get(
                _SPORTSDB_SEARCH,
                params={"p": query},
                timeout=10,
            )
            if resp.status_code == 429 or resp.status_code >= 500:
                wait = 2 ** (attempt + 1)  # 2s, 4s, 8s
                print(
                    f"    [retry {attempt + 1}/{max_retries}] {resp.status_code} for '{query}', waiting {wait}s"
                )
                time.sleep(wait)
                continue
            resp.raise_for_status()
            data = resp.json()
        except (requests.RequestException, ValueError):
            return None

        players = data.get("player") or []
        for p in players:
            if not isinstance(p, dict):
                continue
            if (p.get("strSport") or "").lower() != "soccer":
                continue
            return p.get("strCutout") or p.get("strThumb") or None

        return None

    return None


def fetch_player_photo(player_name: str, *, max_retries: int = 3) -> str | None:
    """Query TheSportsDB for a player photo URL (cutout preferred, then thumb).

    Returns the URL string or None if no soccer player match is found.
    Tries the exact name first, then a cleaned-up variant with apostrophes /
    special quotes stripped (TheSportsDB search can't handle them).
    """
    url = _search_sportsdb(player_name, max_retries=max_retries)
    if url:
        return url

    # Retry with apostrophes / quotes stripped (e.g. "O'Reilly" → "OReilly")
    cleaned = player_name.translate(_SEARCH_STRIP_CHARS)
    if cleaned != player_name:
        return _search_sportsdb(cleaned, max_retries=max_retries)

    return None


def enrich_photos(
    players: list[dict[str, Any]],
    *,
    delay: float = 2.0,
    on_progress: callable | None = None,
) -> int:
    """Add ``photo_url`` to each player dict by querying TheSportsDB.

    Parameters
    ----------
    players:
        List of player dicts (must have ``"name"`` key).  Modified in-place.
    delay:
        Seconds to wait between API calls to avoid rate-limiting.
    on_progress:
        Optional callback ``(index, total, name)`` for progress reporting.

    Returns the number of players for which a photo was found.
    """
    found = 0
    total = len(players)

    for i, player in enumerate(players):
        name = player.get("name")
        if not name:
            continue

        url = fetch_player_photo(name)
        if url:
            player["photo_url"] = url
            found += 1

        if on_progress:
            on_progress(i + 1, total, name)

        # Be polite to the free API
        if i < total - 1:
            time.sleep(delay)

    return found
