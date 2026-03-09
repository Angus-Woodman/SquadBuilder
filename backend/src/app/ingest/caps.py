"""Scrape England international caps and goals from eu-football.info.

The site lists every capped England player across paginated HTML tables.
Each row contains: name, DOB, (death date), year range, caps, goals,
debut date, last match date.

URL pattern:
  Page 1: https://eu-football.info/_players.php?id=60&data=9
  Page N: https://eu-football.info/_players.php?id=60&data=9&page=N
"""

from __future__ import annotations

import re
import time
from datetime import date
from typing import Any

import requests
from bs4 import BeautifulSoup

_BASE_URL = "https://eu-football.info/_players.php"
_DEFAULT_PARAMS = {"id": "60", "data": "9"}


def _parse_date(text: str) -> date | None:
    """Parse a date string like '28 Jul 1993' into a ``date`` object."""
    text = text.strip()
    if not text:
        return None
    try:
        from datetime import datetime

        return datetime.strptime(text, "%d %b %Y").date()
    except ValueError:
        return None


def _parse_int(text: str) -> int | None:
    """Parse an integer from text, returning None if empty / invalid."""
    text = text.strip()
    if not text:
        return None
    try:
        return int(text)
    except ValueError:
        return None


def scrape_page(page: int = 1, *, timeout: int = 15) -> list[dict[str, Any]]:
    """Scrape a single page of England players from eu-football.info.

    Returns a list of dicts with keys:
        name, date_of_birth, caps, goals
    """
    params = dict(_DEFAULT_PARAMS)
    if page > 1:
        params["page"] = str(page)

    resp = requests.get(_BASE_URL, params=params, timeout=timeout)
    resp.raise_for_status()

    soup = BeautifulSoup(resp.text, "html.parser")
    players: list[dict[str, Any]] = []

    # The player data table has rows with 1 <th> (player name) + 7 <td> cells:
    #   th[0]: player name (inside <a> tag)
    #   td[0]: date of birth
    #   td[1]: death date (may be empty)
    #   td[2]: career span (e.g. "2020 - 2025")
    #   td[3]: caps
    #   td[4]: goals (may be empty)
    #   td[5]: debut date
    #   td[6]: last match date
    for table in soup.find_all("table"):
        for tr in table.find_all("tr"):
            ths = tr.find_all("th")
            tds = tr.find_all("td")

            # Data rows have 1 th (name) + 7 tds
            if len(ths) != 1 or len(tds) < 5:
                continue

            # Player name is in the <th> cell
            name_link = ths[0].find("a")
            if not name_link:
                continue
            name = name_link.get_text(strip=True)
            if not name:
                continue

            # DOB is in td[0]
            dob = _parse_date(tds[0].get_text(strip=True))

            # Caps is in td[3]
            caps = _parse_int(tds[3].get_text(strip=True))
            if caps is None:
                continue

            # Goals is in td[4] (may be empty for goalkeepers etc.)
            goals = _parse_int(tds[4].get_text(strip=True))

            players.append(
                {
                    "name": name,
                    "date_of_birth": dob,
                    "caps": caps,
                    "goals": goals if goals is not None else 0,
                }
            )

    return players


def detect_max_page(*, timeout: int = 15) -> int:
    """Detect the last page number from the pagination links on page 1."""
    resp = requests.get(_BASE_URL, params=_DEFAULT_PARAMS, timeout=timeout)
    resp.raise_for_status()

    soup = BeautifulSoup(resp.text, "html.parser")

    # Pagination links look like: <a href="...page=31">31</a>
    max_page = 1
    for a in soup.find_all("a", href=True):
        match = re.search(r"page=(\d+)", a["href"])
        if match:
            page_num = int(match.group(1))
            if page_num > max_page:
                max_page = page_num

    return max_page


def scrape_all_pages(
    *,
    delay: float = 1.0,
    max_pages: int | None = None,
    on_progress: callable | None = None,
) -> list[dict[str, Any]]:
    """Scrape all pages of England players from eu-football.info.

    Parameters
    ----------
    delay:
        Seconds to wait between page requests.
    max_pages:
        If set, stop after this many pages (useful for testing / partial runs).
    on_progress:
        Optional callback ``(page, total_pages, players_so_far)`` for progress.

    Returns a combined list of player dicts.
    """
    total_pages = detect_max_page()
    if max_pages is not None:
        total_pages = min(total_pages, max_pages)

    all_players: list[dict[str, Any]] = []

    for page in range(1, total_pages + 1):
        page_players = scrape_page(page)
        all_players.extend(page_players)

        if on_progress:
            on_progress(page, total_pages, len(all_players))

        if page < total_pages:
            time.sleep(delay)

    return all_players


def match_players(
    scraped: list[dict[str, Any]],
    db_players: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Match scraped caps/goals data to existing DB players.

    Matching strategy:
    1. Exact name match (case-insensitive)
    2. If multiple DB players share a name, use DOB to disambiguate

    Returns a list of dicts with keys: player_id, england_caps, england_goals
    """
    # Build lookup: lowercase name → list of DB players with that name
    from collections import defaultdict

    name_index: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for p in db_players:
        name_index[p["name"].lower()].append(p)

    matched: list[dict[str, Any]] = []

    for sp in scraped:
        candidates = name_index.get(sp["name"].lower(), [])
        if not candidates:
            continue

        if len(candidates) == 1:
            matched.append(
                {
                    "player_id": candidates[0]["player_id"],
                    "england_caps": sp["caps"],
                    "england_goals": sp["goals"],
                }
            )
        else:
            # Disambiguate by DOB
            for c in candidates:
                if c.get("date_of_birth") and sp.get("date_of_birth"):
                    if c["date_of_birth"] == sp["date_of_birth"]:
                        matched.append(
                            {
                                "player_id": c["player_id"],
                                "england_caps": sp["caps"],
                                "england_goals": sp["goals"],
                            }
                        )
                        break

    return matched
