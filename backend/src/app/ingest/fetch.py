import os
from typing import Any

import requests

BASE = "https://api.football-data.org/v4"


def fetch_teams_from_league(league: str) -> dict[str, Any]:
    token = os.getenv("FOOTBALL_DATA_API_TOKEN")
    league = league.strip().upper()
    API_URL = f"{BASE}/competitions/{league}/teams"
    if not token:
        raise RuntimeError(
            "Missing FOOTBALL_DATA_API_TOKEN. Add it to backend/.env or export it in your shell."
        )

    headers = {"X-Auth-Token": token}
    resp = requests.get(API_URL, headers=headers, timeout=30)

    # Helpful error message if rate-limited or unauthorized
    try:
        resp.raise_for_status()
    except requests.HTTPError as e:
        raise RuntimeError(
            f"Request failed: {resp.status_code} {resp.reason}\nBody: {resp.text}"
        ) from e

    return resp.json()
