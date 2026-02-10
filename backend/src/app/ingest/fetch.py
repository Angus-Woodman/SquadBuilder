import os
from typing import Any, Dict

import requests


PL_TEAMS_URL = "https://api.football-data.org/v4/competitions/PL/teams"


def fetch_pl_teams() -> Dict[str, Any]:
    token = os.getenv("FOOTBALL_DATA_API_TOKEN")
    if not token:
        raise RuntimeError(
            "Missing FOOTBALL_DATA_API_TOKEN. Add it to backend/.env or export it in your shell."
        )

    headers = {"X-Auth-Token": token}  # football-data.org auth header :contentReference[oaicite:1]{index=1}
    resp = requests.get(PL_TEAMS_URL, headers=headers, timeout=30)

    # Helpful error message if rate-limited or unauthorized
    if resp.status_code != 200:
        raise RuntimeError(
            f"Request failed: {resp.status_code} {resp.reason}\nBody: {resp.text}"
        )

    return resp.json()
