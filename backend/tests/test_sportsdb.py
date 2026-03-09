"""Tests for the TheSportsDB enrichment module (preferred foot, photos, club)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from app.ingest.sportsdb import (
    _pick_best_match,
    _search_player_id,
    enrich_from_sportsdb,
    fetch_player_details,
    lookup_player,
)


# ---------------------------------------------------------------------------
# _search_player_id
# ---------------------------------------------------------------------------
class TestSearchPlayerId:
    @patch("app.ingest.sportsdb._request_with_retry")
    def test_returns_id_for_soccer_player(self, mock_req: MagicMock) -> None:
        mock_req.return_value = {
            "player": [
                {
                    "idPlayer": "34146220",
                    "strPlayer": "Harry Kane",
                    "strSport": "Soccer",
                }
            ]
        }

        result = _search_player_id("Harry Kane")
        assert result == "34146220"

    @patch("app.ingest.sportsdb._request_with_retry")
    def test_skips_non_soccer(self, mock_req: MagicMock) -> None:
        mock_req.return_value = {
            "player": [
                {
                    "idPlayer": "999",
                    "strPlayer": "Harry Kane",
                    "strSport": "Basketball",
                }
            ]
        }

        result = _search_player_id("Harry Kane")
        assert result is None

    @patch("app.ingest.sportsdb._request_with_retry")
    def test_returns_none_on_empty_response(self, mock_req: MagicMock) -> None:
        mock_req.return_value = {"player": None}

        result = _search_player_id("Unknown Player")
        assert result is None

    @patch("app.ingest.sportsdb._request_with_retry")
    def test_returns_none_on_request_failure(self, mock_req: MagicMock) -> None:
        mock_req.return_value = None

        result = _search_player_id("Test")
        assert result is None

    @patch("app.ingest.sportsdb._request_with_retry")
    def test_retries_with_stripped_apostrophe(self, mock_req: MagicMock) -> None:
        # First call (with apostrophe) → no results
        # Second call (stripped) → found
        mock_req.side_effect = [
            {"player": None},
            {
                "player": [
                    {
                        "idPlayer": "12345",
                        "strPlayer": "Nico OReilly",
                        "strSport": "Soccer",
                    }
                ]
            },
        ]

        result = _search_player_id("Nico O'Reilly")
        assert result == "12345"
        assert mock_req.call_count == 2


# ---------------------------------------------------------------------------
# _pick_best_match (disambiguation)
# ---------------------------------------------------------------------------
class TestPickBestMatch:
    def test_prefers_dob_match(self) -> None:
        players = [
            {
                "idPlayer": "AAA",
                "strSport": "Soccer",
                "dateBorn": "1993-11-07",
                "strTeam": "Rotherham United",
            },
            {
                "idPlayer": "BBB",
                "strSport": "Soccer",
                "dateBorn": "1999-12-08",
                "strTeam": "Chelsea",
            },
        ]
        result = _pick_best_match(players, date_of_birth="1999-12-08", club="Chelsea FC")
        assert result == "BBB"

    def test_prefers_dob_over_club_alone(self) -> None:
        players = [
            {
                "idPlayer": "AAA",
                "strSport": "Soccer",
                "dateBorn": "1993-01-01",
                "strTeam": "Chelsea",
            },
            {
                "idPlayer": "BBB",
                "strSport": "Soccer",
                "dateBorn": "1999-12-08",
                "strTeam": "Rotherham",
            },
        ]
        # DOB match scores +2, club match scores +1 → BBB wins
        result = _pick_best_match(players, date_of_birth="1999-12-08", club="Chelsea FC")
        assert result == "BBB"

    def test_falls_back_to_first_without_hints(self) -> None:
        players = [
            {"idPlayer": "AAA", "strSport": "Soccer"},
            {"idPlayer": "BBB", "strSport": "Soccer"},
        ]
        result = _pick_best_match(players, date_of_birth=None, club=None)
        assert result == "AAA"

    def test_returns_none_for_no_soccer(self) -> None:
        players = [{"idPlayer": "AAA", "strSport": "Basketball"}]
        result = _pick_best_match(players, date_of_birth="2000-01-01")
        assert result is None

    def test_club_substring_match(self) -> None:
        players = [
            {"idPlayer": "AAA", "strSport": "Soccer", "strTeam": "Liverpool"},
            {"idPlayer": "BBB", "strSport": "Soccer", "strTeam": "Chelsea"},
        ]
        result = _pick_best_match(players, club="Chelsea FC")
        assert result == "BBB"


# ---------------------------------------------------------------------------
# lookup_player
# ---------------------------------------------------------------------------
class TestLookupPlayer:
    @patch("app.ingest.sportsdb._request_with_retry")
    def test_returns_player_dict(self, mock_req: MagicMock) -> None:
        mock_req.return_value = {
            "players": [
                {
                    "idPlayer": "34146220",
                    "strPlayer": "Harry Kane",
                    "strSide": "Right",
                    "strPosition": "Centre-Forward",
                    "strTeam": "Bayern Munich",
                    "strCutout": "https://example.com/kane.png",
                }
            ]
        }

        result = lookup_player("34146220")
        assert result is not None
        assert result["strSide"] == "Right"
        assert result["strTeam"] == "Bayern Munich"

    @patch("app.ingest.sportsdb._request_with_retry")
    def test_returns_none_when_empty(self, mock_req: MagicMock) -> None:
        mock_req.return_value = {"players": None}

        result = lookup_player("99999")
        assert result is None

    @patch("app.ingest.sportsdb._request_with_retry")
    def test_returns_none_on_request_failure(self, mock_req: MagicMock) -> None:
        mock_req.return_value = None

        result = lookup_player("12345")
        assert result is None


# ---------------------------------------------------------------------------
# fetch_player_details
# ---------------------------------------------------------------------------
class TestFetchPlayerDetails:
    @patch("app.ingest.sportsdb.lookup_player")
    @patch("app.ingest.sportsdb._search_player_id")
    def test_search_then_lookup(self, mock_search: MagicMock, mock_lookup: MagicMock) -> None:
        mock_search.return_value = "34146220"
        mock_lookup.return_value = {
            "strSide": "Right",
            "strTeam": "Bayern Munich",
        }

        result = fetch_player_details("Harry Kane")
        assert result == {"strSide": "Right", "strTeam": "Bayern Munich"}
        mock_search.assert_called_once_with("Harry Kane", date_of_birth=None, club=None)
        mock_lookup.assert_called_once_with("34146220")

    @patch("app.ingest.sportsdb._search_player_id")
    def test_returns_none_when_search_fails(self, mock_search: MagicMock) -> None:
        mock_search.return_value = None

        result = fetch_player_details("Unknown Player")
        assert result is None


# ---------------------------------------------------------------------------
# enrich_from_sportsdb
# ---------------------------------------------------------------------------
class TestEnrichFromSportsdb:
    @patch("app.ingest.sportsdb.time.sleep")
    @patch("app.ingest.sportsdb.fetch_player_details")
    def test_adds_preferred_foot(self, mock_fetch: MagicMock, mock_sleep: MagicMock) -> None:
        mock_fetch.return_value = {
            "strSide": "Right",
            "strCutout": "https://example.com/photo.png",
            "strTeam": "Arsenal",
        }

        players = [
            {
                "player_id": 1,
                "name": "Bukayo Saka",
                "photo_url": "existing.png",
                "club": "Arsenal FC",
            },
        ]

        found = enrich_from_sportsdb(players, delay=0)

        assert found == 1
        assert players[0]["preferred_foot"] == "Right"
        # Existing photo_url should NOT be overwritten
        assert players[0]["photo_url"] == "existing.png"
        # Existing club should NOT be overwritten
        assert players[0]["club"] == "Arsenal FC"

    @patch("app.ingest.sportsdb.time.sleep")
    @patch("app.ingest.sportsdb.fetch_player_details")
    def test_fills_missing_photo_and_club(
        self, mock_fetch: MagicMock, mock_sleep: MagicMock
    ) -> None:
        mock_fetch.return_value = {
            "strSide": "Left",
            "strCutout": "https://example.com/photo.png",
            "strTeam": "Bayern Munich",
        }

        players = [
            {"player_id": 1, "name": "Harry Kane", "photo_url": None, "club": None},
        ]

        found = enrich_from_sportsdb(players, delay=0)

        assert found == 1
        assert players[0]["preferred_foot"] == "Left"
        assert players[0]["photo_url"] == "https://example.com/photo.png"
        assert players[0]["club"] == "Bayern Munich"

    @patch("app.ingest.sportsdb.time.sleep")
    @patch("app.ingest.sportsdb.fetch_player_details")
    def test_returns_zero_when_no_data(self, mock_fetch: MagicMock, mock_sleep: MagicMock) -> None:
        mock_fetch.return_value = None

        players = [
            {"player_id": 1, "name": "Unknown Player"},
        ]

        found = enrich_from_sportsdb(players, delay=0)

        assert found == 0
        assert "preferred_foot" not in players[0]

    @patch("app.ingest.sportsdb.time.sleep")
    @patch("app.ingest.sportsdb.fetch_player_details")
    def test_calls_progress_callback(self, mock_fetch: MagicMock, mock_sleep: MagicMock) -> None:
        mock_fetch.return_value = {"strSide": "Right"}

        progress_calls: list = []

        def on_progress(i: int, total: int, name: str) -> None:
            progress_calls.append((i, total, name))

        players = [
            {"player_id": 1, "name": "Saka"},
            {"player_id": 2, "name": "Rice"},
        ]

        enrich_from_sportsdb(players, delay=0, on_progress=on_progress)

        assert len(progress_calls) == 2
        assert progress_calls[0] == (1, 2, "Saka")
        assert progress_calls[1] == (2, 2, "Rice")

    @patch("app.ingest.sportsdb.time.sleep")
    @patch("app.ingest.sportsdb.fetch_player_details")
    def test_skips_player_without_name(self, mock_fetch: MagicMock, mock_sleep: MagicMock) -> None:
        players = [{"player_id": 1, "name": None}]

        found = enrich_from_sportsdb(players, delay=0)

        assert found == 0
        mock_fetch.assert_not_called()


# ---------------------------------------------------------------------------
# Integration: update_player_sportsdb
# ---------------------------------------------------------------------------
class TestUpdatePlayerSportsdb:
    def test_updates_preferred_foot(self, db) -> None:
        from conftest import create_player_in_db

        from app.db.store import update_player_sportsdb

        create_player_in_db(db, player_id=10, name="Harry Kane")

        players = [
            {
                "player_id": 10,
                "preferred_foot": "Right",
                "photo_url": "https://example.com/kane.png",
                "club": "Bayern Munich",
            },
        ]

        updated = update_player_sportsdb(players)
        assert updated == 1

        from app.db.models import Player

        kane = db.get(Player, 10)
        db.refresh(kane)
        assert kane.preferred_foot == "Right"
        assert kane.photo_url == "https://example.com/kane.png"
        assert kane.club == "Bayern Munich"

    def test_skips_when_no_data(self, db) -> None:
        from conftest import create_player_in_db

        from app.db.store import update_player_sportsdb

        create_player_in_db(db, player_id=10, name="Test Player")

        updated = update_player_sportsdb([{"player_id": 10}])
        assert updated == 0

    def test_partial_update(self, db) -> None:
        from conftest import create_player_in_db

        from app.db.store import update_player_sportsdb

        create_player_in_db(
            db, player_id=10, name="Saka", photo_url="existing.png", club="Arsenal FC"
        )

        # Only update preferred_foot, don't touch photo or club
        updated = update_player_sportsdb(
            [
                {"player_id": 10, "preferred_foot": "Right"},
            ]
        )
        assert updated == 1

        from app.db.models import Player

        saka = db.get(Player, 10)
        db.refresh(saka)
        assert saka.preferred_foot == "Right"
        assert saka.photo_url == "existing.png"
        assert saka.club == "Arsenal FC"
