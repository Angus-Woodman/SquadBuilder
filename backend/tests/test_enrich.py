"""Tests for the player photo enrichment module."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from app.ingest.enrich import enrich_photos, fetch_player_photo


# ---------------------------------------------------------------------------
# fetch_player_photo
# ---------------------------------------------------------------------------
class TestFetchPlayerPhoto:
    """Unit tests for ``fetch_player_photo``."""

    @patch("app.ingest.enrich.requests.get")
    def test_returns_cutout_when_available(self, mock_get: MagicMock) -> None:
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = {
            "player": [
                {
                    "strPlayer": "Harry Kane",
                    "strSport": "Soccer",
                    "strCutout": "https://example.com/cutout.png",
                    "strThumb": "https://example.com/thumb.jpg",
                }
            ]
        }
        mock_get.return_value.raise_for_status = MagicMock()

        result = fetch_player_photo("Harry Kane")
        assert result == "https://example.com/cutout.png"

    @patch("app.ingest.enrich.requests.get")
    def test_falls_back_to_thumb(self, mock_get: MagicMock) -> None:
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = {
            "player": [
                {
                    "strPlayer": "Harry Kane",
                    "strSport": "Soccer",
                    "strCutout": "",
                    "strThumb": "https://example.com/thumb.jpg",
                }
            ]
        }
        mock_get.return_value.raise_for_status = MagicMock()

        result = fetch_player_photo("Harry Kane")
        assert result == "https://example.com/thumb.jpg"

    @patch("app.ingest.enrich.requests.get")
    def test_filters_non_soccer(self, mock_get: MagicMock) -> None:
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = {
            "player": [
                {
                    "strPlayer": "Harry Kane",
                    "strSport": "Baseball",
                    "strCutout": "https://example.com/wrong.png",
                }
            ]
        }
        mock_get.return_value.raise_for_status = MagicMock()

        result = fetch_player_photo("Harry Kane")
        assert result is None

    @patch("app.ingest.enrich.requests.get")
    def test_returns_none_when_no_results(self, mock_get: MagicMock) -> None:
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = {"player": None}
        mock_get.return_value.raise_for_status = MagicMock()

        result = fetch_player_photo("Nonexistent Player")
        assert result is None

    @patch("app.ingest.enrich.requests.get")
    def test_returns_none_on_request_error(self, mock_get: MagicMock) -> None:
        import requests

        mock_get.side_effect = requests.RequestException("timeout")

        result = fetch_player_photo("Harry Kane")
        assert result is None


# ---------------------------------------------------------------------------
# enrich_photos
# ---------------------------------------------------------------------------
class TestEnrichPhotos:
    """Unit tests for ``enrich_photos``."""

    @patch("app.ingest.enrich.fetch_player_photo")
    def test_sets_photo_url_on_players(self, mock_fetch: MagicMock) -> None:
        mock_fetch.side_effect = [
            "https://example.com/kane.png",
            None,
            "https://example.com/saka.png",
        ]
        players = [
            {"player_id": 1, "name": "Harry Kane"},
            {"player_id": 2, "name": "Unknown Player"},
            {"player_id": 3, "name": "Bukayo Saka"},
        ]

        found = enrich_photos(players, delay=0)

        assert found == 2
        assert players[0]["photo_url"] == "https://example.com/kane.png"
        assert players[1].get("photo_url") is None
        assert players[2]["photo_url"] == "https://example.com/saka.png"

    @patch("app.ingest.enrich.fetch_player_photo")
    def test_calls_progress_callback(self, mock_fetch: MagicMock) -> None:
        mock_fetch.return_value = "https://example.com/photo.png"
        players = [{"player_id": 1, "name": "Harry Kane"}]

        progress_calls: list[tuple] = []

        def on_progress(i: int, total: int, name: str) -> None:
            progress_calls.append((i, total, name))

        enrich_photos(players, delay=0, on_progress=on_progress)

        assert progress_calls == [(1, 1, "Harry Kane")]

    @patch("app.ingest.enrich.fetch_player_photo")
    def test_returns_zero_on_empty_list(self, mock_fetch: MagicMock) -> None:
        found = enrich_photos([], delay=0)
        assert found == 0
        mock_fetch.assert_not_called()


# ---------------------------------------------------------------------------
# Integration: update_player_photos
# ---------------------------------------------------------------------------
class TestUpdatePlayerPhotos:
    """Integration test for updating player photos in the DB."""

    def test_update_player_photos(self, db) -> None:
        from conftest import create_player_in_db

        from app.db.store import update_player_photos

        create_player_in_db(db, player_id=10, name="Harry Kane")
        create_player_in_db(db, player_id=20, name="Bukayo Saka")

        player_dicts = [
            {"player_id": 10, "name": "Harry Kane", "photo_url": "https://example.com/kane.png"},
            {"player_id": 20, "name": "Bukayo Saka"},  # no photo_url
        ]

        updated = update_player_photos(player_dicts)
        assert updated == 1

        from app.db.models import Player

        kane = db.get(Player, 10)
        assert kane.photo_url == "https://example.com/kane.png"

        saka = db.get(Player, 20)
        assert saka.photo_url is None
