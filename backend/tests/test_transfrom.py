# backend/tests/test_transform.py

from __future__ import annotations

from datetime import date
from typing import Any

import pytest

from app.ingest.transform import (
    transform_competition_teams_payload,
    transform_many_competitions,
)


def _make_payload_team_with_squad(
    *,
    team_id: int = 1,
    team_name: str = "Team A",
    squad: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    return {
        "teams": [
            {
                "id": team_id,
                "name": team_name,
                "shortName": team_name,
                "tla": "TMA",
                "crest": "https://example.com/crest.png",
                "website": "https://example.com",
                "founded": 1900,
                "clubColors": "Red / White",
                "venue": "Example Stadium",
                "area": {"id": 2072, "name": "England", "code": "ENG"},
                "coach": {
                    "id": 123,
                    "name": "Coach Name",
                    "nationality": "England",
                    "dateOfBirth": "1980-01-01",
                    "contract": {"start": "2024-07", "until": "2027-06"},
                },
                "squad": squad or [],
                "lastUpdated": "2024-07-29T17:18:23Z",
            }
        ]
    }


def test_transform_competition_teams_payload_happy_path() -> None:
    payload = _make_payload_team_with_squad(
        team_id=397,
        team_name="Brighton & Hove Albion FC",
        squad=[
            {
                "id": 4040,
                "name": "Jason Steele",
                "position": "Goalkeeper",
                "dateOfBirth": "1990-08-18",
                "nationality": "England",
            },
            {
                "id": 126870,
                "name": "Bart Verbruggen",
                "position": "Goalkeeper",
                "dateOfBirth": "2002-08-18",
                "nationality": "Netherlands",
            },
        ],
    )

    out = transform_competition_teams_payload(payload, competition_code="pl")

    assert out["competition_code"] == "PL"
    assert out["counts"]["teams"] == 1
    assert out["counts"]["players"] == 2
    assert out["counts"]["team_players"] == 2

    team = out["teams"][0]
    assert team["team_id"] == 397
    assert team["competition_code"] == "PL"
    assert team["name"] == "Brighton & Hove Albion FC"
    assert team["area_code"] == "ENG"
    assert team["coach_name"] == "Coach Name"

    players = sorted(out["players"], key=lambda p: p["player_id"])
    assert players[0]["player_id"] == 4040
    assert players[0]["name"] == "Jason Steele"
    assert players[0]["nationality"] == "England"
    assert players[0]["date_of_birth"] == date(1990, 8, 18)

    assert players[1]["player_id"] == 126870
    assert players[1]["date_of_birth"] == date(2002, 8, 18)

    links = sorted(out["team_players"], key=lambda x: x["player_id"])
    assert links == [{"team_id": 397, "player_id": 4040}, {"team_id": 397, "player_id": 126870}]


def test_transform_handles_missing_optional_player_fields() -> None:
    payload = _make_payload_team_with_squad(
        team_id=10,
        squad=[
            {"id": 1, "name": "No DOB", "position": "Midfield", "nationality": "England"},
            {"id": 2, "name": "No Position", "dateOfBirth": "2000-01-01", "nationality": "England"},
            {"id": 3, "name": "Invalid DOB", "dateOfBirth": "not-a-date", "nationality": "England"},
        ],
    )

    out = transform_competition_teams_payload(payload, competition_code="PL")
    players = {p["player_id"]: p for p in out["players"]}

    assert players[1]["date_of_birth"] is None
    assert players[2]["position"] is None
    assert players[3]["date_of_birth"] is None


def test_transform_many_competitions_dedupes_players_but_keeps_relationships() -> None:
    # Same player id appears in two competitions/teams
    shared_player = {
        "id": 999,
        "name": "Shared Player",
        "position": "Centre-Back",
        "dateOfBirth": "1999-12-31",
        "nationality": "England",
    }

    pl_payload = _make_payload_team_with_squad(
        team_id=1,
        team_name="PL Team",
        squad=[shared_player, {"id": 1000, "name": "PL Only", "nationality": "England"}],
    )
    sa_payload = _make_payload_team_with_squad(
        team_id=2,
        team_name="SA Team",
        squad=[shared_player, {"id": 2000, "name": "SA Only", "nationality": "Spain"}],
    )

    combined = transform_many_competitions({"PL": pl_payload, "SA": sa_payload})

    # Players deduped by player_id => 3 total unique players
    assert combined["counts"]["players"] == 3

    # team_players should include both relationships for shared player
    shared_links = [tp for tp in combined["team_players"] if tp["player_id"] == 999]
    assert sorted(shared_links, key=lambda x: x["team_id"]) == [
        {"team_id": 1, "player_id": 999},
        {"team_id": 2, "player_id": 999},
    ]


def test_transform_competition_code_normalized() -> None:
    payload = _make_payload_team_with_squad(team_id=1, squad=[])
    out = transform_competition_teams_payload(payload, competition_code="  pl  ")
    assert out["competition_code"] == "PL"


def test_transform_raises_if_teams_is_not_list() -> None:
    payload = {"teams": {"not": "a list"}}
    with pytest.raises(ValueError, match="payload\\['teams'\\]"):
        transform_competition_teams_payload(payload, competition_code="PL")
