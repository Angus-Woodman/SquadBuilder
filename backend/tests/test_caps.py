"""Tests for the England caps/goals scraping and matching module."""

from __future__ import annotations

from datetime import date
from unittest.mock import MagicMock, patch

from app.ingest.caps import (
    _parse_date,
    _parse_int,
    match_players,
    scrape_page,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
class TestParseDate:
    def test_valid_date(self) -> None:
        assert _parse_date("28 Jul 1993") == date(1993, 7, 28)

    def test_empty_string(self) -> None:
        assert _parse_date("") is None

    def test_invalid_string(self) -> None:
        assert _parse_date("not a date") is None


class TestParseInt:
    def test_valid_int(self) -> None:
        assert _parse_int("112") == 112

    def test_empty_string(self) -> None:
        assert _parse_int("") is None

    def test_whitespace(self) -> None:
        assert _parse_int("  78  ") == 78

    def test_invalid(self) -> None:
        assert _parse_int("abc") is None


# ---------------------------------------------------------------------------
# scrape_page
# ---------------------------------------------------------------------------
_SAMPLE_HTML = """
<html><body>
<table>
  <tr>
    <th>Footballer</th>
    <th>Born</th>
    <th>Died</th>
    <th>Period</th>
    <th>Caps</th>
    <th>Goals</th>
    <th>Debut</th>
    <th>Last</th>
  </tr>
  <tr>
    <th><a href="/player/1">Harry Kane</a></th>
    <td>28 Jul 1993</td>
    <td></td>
    <td>2015 - 2025</td>
    <td>112</td>
    <td>78</td>
    <td>27 Mar 2015</td>
    <td>16 Nov 2025</td>
  </tr>
  <tr>
    <th><a href="/player/2">Jordan Pickford</a></th>
    <td>07 Mar 1994</td>
    <td></td>
    <td>2017 - 2025</td>
    <td>81</td>
    <td></td>
    <td>10 Nov 2017</td>
    <td>13 Nov 2025</td>
  </tr>
  <tr>
    <td>Some header</td>
    <td>Not a player row</td>
  </tr>
</table>
</body></html>
"""


class TestScrapePage:
    @patch("app.ingest.caps.requests.get")
    def test_parses_player_rows(self, mock_get: MagicMock) -> None:
        mock_resp = MagicMock()
        mock_resp.text = _SAMPLE_HTML
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        players = scrape_page(1)

        assert len(players) == 2
        assert players[0] == {
            "name": "Harry Kane",
            "date_of_birth": date(1993, 7, 28),
            "caps": 112,
            "goals": 78,
        }
        assert players[1] == {
            "name": "Jordan Pickford",
            "date_of_birth": date(1994, 3, 7),
            "caps": 81,
            "goals": 0,  # empty goals → 0
        }

    @patch("app.ingest.caps.requests.get")
    def test_handles_empty_table(self, mock_get: MagicMock) -> None:
        mock_resp = MagicMock()
        mock_resp.text = "<html><body><table></table></body></html>"
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        players = scrape_page(1)
        assert players == []

    @patch("app.ingest.caps.requests.get")
    def test_passes_page_param_for_page_2(self, mock_get: MagicMock) -> None:
        mock_resp = MagicMock()
        mock_resp.text = "<html><body><table></table></body></html>"
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        scrape_page(2)

        call_kwargs = mock_get.call_args
        assert (
            call_kwargs.kwargs.get("params", {}).get("page") == "2"
            or call_kwargs[1].get("params", {}).get("page") == "2"
        )

    @patch("app.ingest.caps.requests.get")
    def test_no_page_param_for_page_1(self, mock_get: MagicMock) -> None:
        mock_resp = MagicMock()
        mock_resp.text = "<html><body><table></table></body></html>"
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        scrape_page(1)

        call_kwargs = mock_get.call_args
        params = call_kwargs.kwargs.get("params") or call_kwargs[1].get("params", {})
        assert "page" not in params


# ---------------------------------------------------------------------------
# match_players
# ---------------------------------------------------------------------------
class TestMatchPlayers:
    def test_exact_name_match(self) -> None:
        scraped = [
            {"name": "Harry Kane", "date_of_birth": date(1993, 7, 28), "caps": 112, "goals": 78},
        ]
        db_players = [
            {"player_id": 100, "name": "Harry Kane", "date_of_birth": date(1993, 7, 28)},
        ]

        result = match_players(scraped, db_players)

        assert len(result) == 1
        assert result[0] == {"player_id": 100, "england_caps": 112, "england_goals": 78}

    def test_case_insensitive_match(self) -> None:
        scraped = [
            {"name": "harry kane", "date_of_birth": None, "caps": 112, "goals": 78},
        ]
        db_players = [
            {"player_id": 100, "name": "Harry Kane", "date_of_birth": None},
        ]

        result = match_players(scraped, db_players)
        assert len(result) == 1

    def test_no_match(self) -> None:
        scraped = [
            {"name": "Peter Shilton", "date_of_birth": None, "caps": 125, "goals": 0},
        ]
        db_players = [
            {"player_id": 100, "name": "Harry Kane", "date_of_birth": None},
        ]

        result = match_players(scraped, db_players)
        assert len(result) == 0

    def test_disambiguates_by_dob(self) -> None:
        """When two DB players share a name, DOB breaks the tie."""
        scraped = [
            {"name": "Gary Stevens", "date_of_birth": date(1963, 3, 27), "caps": 46, "goals": 0},
        ]
        db_players = [
            {"player_id": 10, "name": "Gary Stevens", "date_of_birth": date(1962, 3, 27)},
            {"player_id": 20, "name": "Gary Stevens", "date_of_birth": date(1963, 3, 27)},
        ]

        result = match_players(scraped, db_players)

        assert len(result) == 1
        assert result[0]["player_id"] == 20

    def test_empty_scraped_list(self) -> None:
        result = match_players([], [{"player_id": 1, "name": "Test"}])
        assert result == []


# ---------------------------------------------------------------------------
# Integration: update_player_caps
# ---------------------------------------------------------------------------
class TestUpdatePlayerCaps:
    """Integration test for updating caps/goals in the DB."""

    def test_update_player_caps(self, db) -> None:
        from conftest import create_player_in_db

        from app.db.store import update_player_caps

        create_player_in_db(db, player_id=10, name="Harry Kane")
        create_player_in_db(db, player_id=20, name="Bukayo Saka")

        matched = [
            {"player_id": 10, "england_caps": 112, "england_goals": 78},
            {"player_id": 20, "england_caps": 48, "england_goals": 14},
        ]

        updated = update_player_caps(matched)
        assert updated == 2

        from app.db.models import Player

        kane = db.get(Player, 10)
        db.refresh(kane)
        assert kane.england_caps == 112
        assert kane.england_goals == 78

        saka = db.get(Player, 20)
        db.refresh(saka)
        assert saka.england_caps == 48
        assert saka.england_goals == 14

    def test_skips_when_caps_is_none(self, db) -> None:
        from conftest import create_player_in_db

        from app.db.store import update_player_caps

        create_player_in_db(db, player_id=10, name="Test Player")

        updated = update_player_caps([{"player_id": 10, "england_goals": 5}])
        assert updated == 0
