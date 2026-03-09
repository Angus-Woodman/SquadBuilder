"""Tests for the Understat season stats scraping and matching module."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from app.ingest.season_stats import (
    _normalise_name,
    fetch_all_leagues,
    fetch_league_players,
    match_players,
)


# ---------------------------------------------------------------------------
# _normalise_name
# ---------------------------------------------------------------------------
class TestNormaliseName:
    def test_lowercase(self) -> None:
        assert _normalise_name("Harry Kane") == "harry kane"

    def test_strips_accents(self) -> None:
        assert _normalise_name("Héctor Bellerín") == "hector bellerin"

    def test_strips_whitespace(self) -> None:
        assert _normalise_name("  Phil Foden  ") == "phil foden"

    def test_empty_string(self) -> None:
        assert _normalise_name("") == ""


# ---------------------------------------------------------------------------
# fetch_league_players
# ---------------------------------------------------------------------------
class TestFetchLeaguePlayers:
    @patch("app.ingest.season_stats.requests.post")
    def test_returns_players_on_success(self, mock_post: MagicMock) -> None:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "success": True,
            "players": [
                {
                    "id": "8260",
                    "player_name": "Erling Haaland",
                    "games": "28",
                    "time": "2349",
                    "goals": "22",
                    "assists": "7",
                    "xG": "22.83",
                    "xA": "4.68",
                    "shots": "98",
                    "key_passes": "20",
                    "yellow_cards": "1",
                    "red_cards": "0",
                    "position": "F S",
                    "team_title": "Manchester City",
                },
            ],
        }
        mock_resp.raise_for_status = MagicMock()
        mock_post.return_value = mock_resp

        result = fetch_league_players("EPL")

        assert len(result) == 1
        assert result[0]["player_name"] == "Erling Haaland"
        assert result[0]["goals"] == "22"

        # Verify POST was called with correct data
        mock_post.assert_called_once()
        call_kwargs = mock_post.call_args
        assert call_kwargs.kwargs["data"] == {"league": "EPL", "season": "2025"}

    @patch("app.ingest.season_stats.requests.post")
    def test_returns_empty_on_failure(self, mock_post: MagicMock) -> None:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"success": False}
        mock_resp.raise_for_status = MagicMock()
        mock_post.return_value = mock_resp

        result = fetch_league_players("EPL")
        assert result == []

    @patch("app.ingest.season_stats.requests.post")
    def test_raises_on_http_error(self, mock_post: MagicMock) -> None:
        mock_resp = MagicMock()
        mock_resp.raise_for_status.side_effect = Exception("500 Server Error")
        mock_post.return_value = mock_resp

        with pytest.raises(Exception, match="500"):
            fetch_league_players("EPL")


# ---------------------------------------------------------------------------
# fetch_all_leagues
# ---------------------------------------------------------------------------
class TestFetchAllLeagues:
    @patch("app.ingest.season_stats.fetch_league_players")
    @patch("app.ingest.season_stats.time.sleep")
    def test_fetches_multiple_leagues(self, mock_sleep: MagicMock, mock_fetch: MagicMock) -> None:
        mock_fetch.side_effect = [
            [{"player_name": "Saka", "id": "1"}],
            [{"player_name": "Kane", "id": "2"}],
        ]

        result = fetch_all_leagues(leagues=["EPL", "Bundesliga"], delay=0.5)

        assert len(result) == 2
        assert result[0]["player_name"] == "Saka"
        assert result[0]["_league"] == "EPL"
        assert result[1]["player_name"] == "Kane"
        assert result[1]["_league"] == "Bundesliga"

        mock_sleep.assert_called_once_with(0.5)

    @patch("app.ingest.season_stats.fetch_league_players")
    @patch("app.ingest.season_stats.time.sleep")
    def test_calls_progress_callback(self, mock_sleep: MagicMock, mock_fetch: MagicMock) -> None:
        mock_fetch.return_value = [{"player_name": "Test", "id": "1"}]
        progress_calls: list = []

        def on_progress(i: int, total: int, league: str, count: int) -> None:
            progress_calls.append((i, total, league, count))

        fetch_all_leagues(leagues=["EPL"], delay=0, on_progress=on_progress)

        assert len(progress_calls) == 1
        assert progress_calls[0] == (1, 1, "EPL", 1)


# ---------------------------------------------------------------------------
# match_players
# ---------------------------------------------------------------------------
class TestMatchPlayers:
    def test_exact_name_match(self) -> None:
        understat = [
            {
                "player_name": "Bukayo Saka",
                "games": "25",
                "time": "1763",
                "goals": "6",
                "assists": "10",
                "xG": "8.94",
                "xA": "11.58",
                "shots": "55",
                "key_passes": "40",
                "yellow_cards": "3",
                "red_cards": "0",
                "team_title": "Arsenal",
            },
        ]
        db_players = [
            {"player_id": 100, "name": "Bukayo Saka", "club": "Arsenal FC"},
        ]

        result = match_players(understat, db_players)

        assert len(result) == 1
        assert result[0]["player_id"] == 100
        assert result[0]["season_games"] == 25
        assert result[0]["season_minutes"] == 1763
        assert result[0]["season_goals"] == 6
        assert result[0]["season_assists"] == 10
        assert result[0]["season_xg"] == "8.94"
        assert result[0]["season_xa"] == "11.58"
        assert result[0]["season_shots"] == 55
        assert result[0]["season_key_passes"] == 40
        assert result[0]["season_yellow_cards"] == 3
        assert result[0]["season_red_cards"] == 0

    def test_case_insensitive_match(self) -> None:
        understat = [
            {
                "player_name": "harry kane",
                "games": "24",
                "time": "1968",
                "goals": "30",
                "assists": "5",
                "xG": "0",
                "xA": "0",
                "shots": "0",
                "key_passes": "0",
                "yellow_cards": "0",
                "red_cards": "0",
                "team_title": "Bayern Munich",
            },
        ]
        db_players = [
            {"player_id": 50, "name": "Harry Kane", "club": None},
        ]

        result = match_players(understat, db_players)
        assert len(result) == 1
        assert result[0]["season_goals"] == 30

    def test_accent_insensitive_match(self) -> None:
        understat = [
            {
                "player_name": "Héctor Bellerín",
                "games": "10",
                "time": "800",
                "goals": "0",
                "assists": "2",
                "xG": "0",
                "xA": "0",
                "shots": "0",
                "key_passes": "0",
                "yellow_cards": "0",
                "red_cards": "0",
                "team_title": "Some Club",
            },
        ]
        db_players = [
            {"player_id": 60, "name": "Hector Bellerin", "club": None},
        ]

        result = match_players(understat, db_players)
        assert len(result) == 1

    def test_no_match(self) -> None:
        understat = [
            {
                "player_name": "Lionel Messi",
                "games": "20",
                "time": "1500",
                "goals": "15",
                "assists": "10",
                "xG": "0",
                "xA": "0",
                "shots": "0",
                "key_passes": "0",
                "yellow_cards": "0",
                "red_cards": "0",
                "team_title": "Inter Miami",
            },
        ]
        db_players = [
            {"player_id": 100, "name": "Harry Kane", "club": None},
        ]

        result = match_players(understat, db_players)
        assert result == []

    def test_picks_most_minutes_on_duplicate(self) -> None:
        """When a player transferred mid-season and appears in two leagues."""
        understat = [
            {
                "player_name": "Test Player",
                "games": "10",
                "time": "800",
                "goals": "3",
                "assists": "1",
                "xG": "0",
                "xA": "0",
                "shots": "0",
                "key_passes": "0",
                "yellow_cards": "0",
                "red_cards": "0",
                "team_title": "Old Club",
            },
            {
                "player_name": "Test Player",
                "games": "15",
                "time": "1200",
                "goals": "5",
                "assists": "2",
                "xG": "0",
                "xA": "0",
                "shots": "0",
                "key_passes": "0",
                "yellow_cards": "0",
                "red_cards": "0",
                "team_title": "New Club",
            },
        ]
        db_players = [
            {"player_id": 70, "name": "Test Player", "club": None},
        ]

        result = match_players(understat, db_players)
        assert len(result) == 1
        assert result[0]["season_minutes"] == 1200
        assert result[0]["season_goals"] == 5

    def test_fills_missing_club(self) -> None:
        """When DB player has no club, fill from Understat team_title."""
        understat = [
            {
                "player_name": "Bukayo Saka",
                "games": "25",
                "time": "1763",
                "goals": "6",
                "assists": "10",
                "xG": "0",
                "xA": "0",
                "shots": "0",
                "key_passes": "0",
                "yellow_cards": "0",
                "red_cards": "0",
                "team_title": "Arsenal",
            },
        ]
        db_players = [
            {"player_id": 100, "name": "Bukayo Saka", "club": None},
        ]

        result = match_players(understat, db_players)
        assert result[0].get("club") == "Arsenal"

    def test_does_not_overwrite_existing_club(self) -> None:
        """When DB player already has a club, don't replace it."""
        understat = [
            {
                "player_name": "Bukayo Saka",
                "games": "25",
                "time": "1763",
                "goals": "6",
                "assists": "10",
                "xG": "0",
                "xA": "0",
                "shots": "0",
                "key_passes": "0",
                "yellow_cards": "0",
                "red_cards": "0",
                "team_title": "Arsenal",
            },
        ]
        db_players = [
            {"player_id": 100, "name": "Bukayo Saka", "club": "Arsenal FC"},
        ]

        result = match_players(understat, db_players)
        assert "club" not in result[0]

    def test_empty_understat(self) -> None:
        result = match_players([], [{"player_id": 1, "name": "Test"}])
        assert result == []


# ---------------------------------------------------------------------------
# Integration: update_player_season_stats
# ---------------------------------------------------------------------------
class TestUpdatePlayerSeasonStats:
    def test_updates_season_stats(self, db) -> None:
        from conftest import create_player_in_db

        from app.db.store import update_player_season_stats

        create_player_in_db(db, player_id=10, name="Bukayo Saka", club="Arsenal FC")

        matched = [
            {
                "player_id": 10,
                "season_games": 25,
                "season_minutes": 1763,
                "season_goals": 6,
                "season_assists": 10,
                "season_xg": "8.94",
                "season_xa": "11.58",
                "season_yellow_cards": 3,
                "season_red_cards": 0,
                "season_key_passes": 40,
                "season_shots": 55,
            },
        ]

        updated = update_player_season_stats(matched)
        assert updated == 1

        from app.db.models import Player

        saka = db.get(Player, 10)
        db.refresh(saka)
        assert saka.season_games == 25
        assert saka.season_minutes == 1763
        assert saka.season_goals == 6
        assert saka.season_assists == 10
        assert saka.season_xg == "8.94"
        assert saka.season_xa == "11.58"
        assert saka.season_yellow_cards == 3
        assert saka.season_red_cards == 0
        assert saka.season_key_passes == 40
        assert saka.season_shots == 55

    def test_backfills_club(self, db) -> None:
        from conftest import create_player_in_db

        from app.db.store import update_player_season_stats

        create_player_in_db(db, player_id=20, name="Harry Kane", club=None)

        matched = [
            {
                "player_id": 20,
                "season_games": 24,
                "season_minutes": 1968,
                "season_goals": 30,
                "season_assists": 5,
                "club": "Bayern Munich",
            },
        ]

        updated = update_player_season_stats(matched)
        assert updated == 1

        from app.db.models import Player

        kane = db.get(Player, 20)
        db.refresh(kane)
        assert kane.club == "Bayern Munich"
        assert kane.season_goals == 30

    def test_skips_when_minutes_is_none(self, db) -> None:
        from conftest import create_player_in_db

        from app.db.store import update_player_season_stats

        create_player_in_db(db, player_id=10, name="Test Player")

        updated = update_player_season_stats([{"player_id": 10, "season_goals": 5}])
        assert updated == 0
