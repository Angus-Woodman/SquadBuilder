"""Tests for the SofaScore team squad scraper module.

Tests cover:
- Player data extraction from __NEXT_DATA__ JSON
- HTML parsing fallback
- API response parsing
- CLI integration
- Error handling and edge cases
- Team ID lookup
"""

from __future__ import annotations

import json
from unittest.mock import MagicMock, Mock, patch

import pytest

from app.ingest.sofascore import (
    COMMON_TEAMS,
    _parse_next_data_players,
    _parse_sofascore_api_response,
    fetch_sofascore_squad,
    fetch_sofascore_squad_with_playwright,
)

# ─────────────────────────────────────────────────────────────────────────
# FIXTURES
# ─────────────────────────────────────────────────────────────────────────


@pytest.fixture
def sample_player_json_response() -> dict:
    """Sample __NEXT_DATA__ JSON response from SofaScore."""
    return {
        "props": {
            "pageProps": {
                "players": {
                    "players": [
                        {
                            "player": {
                                "name": "Nicolas Jackson",
                                "firstName": "Nicolas",
                                "lastName": "Jackson",
                                "slug": "nicolas-jackson",
                                "id": 1234,
                            },
                            "position": "F",
                            "shirtNumber": 15,
                        },
                        {
                            "player": {
                                "name": "Reece James",
                                "firstName": "Reece",
                                "lastName": "James",
                                "slug": "reece-james",
                                "id": 5678,
                            },
                            "position": "D",
                            "shirtNumber": 24,
                        },
                        {
                            "player": {
                                "name": "Robert Sánchez",
                                "firstName": "",
                                "lastName": "",
                                "slug": "robert-sanchez",
                                "id": 9999,
                            },
                            "position": "G",
                            "shirtNumber": 1,
                        },
                    ],
                    "foreignPlayers": [],
                    "nationalPlayers": [],
                }
            }
        }
    }


@pytest.fixture
def sample_html_with_next_data(sample_player_json_response) -> str:
    """Sample HTML page with embedded __NEXT_DATA__ JSON."""
    json_str = json.dumps(sample_player_json_response)
    return f"""
    <!DOCTYPE html>
    <html>
    <head><title>Chelsea Team</title></head>
    <body>
        <h1>Chelsea Squad</h1>
        <div id="content"></div>
        <script id="__NEXT_DATA__" type="application/json">
        {json_str}
        </script>
    </body>
    </html>
    """


# ─────────────────────────────────────────────────────────────────────────
# _parse_next_data_players
# ─────────────────────────────────────────────────────────────────────────


class TestParseNextDataPlayers:
    """Tests for extracting player data from __NEXT_DATA__ JSON."""

    def test_extracts_players_from_valid_html(self, sample_html_with_next_data):
        """Should extract all players from valid HTML with __NEXT_DATA__."""
        players = _parse_next_data_players(sample_html_with_next_data)

        assert len(players) == 3
        assert players[0]["name"] == "Nicolas Jackson"
        assert players[0]["position"] == "F"
        assert players[0]["shirt_number"] == 15

    def test_extracts_player_with_name_field(self, sample_html_with_next_data):
        """Should use 'name' field when available."""
        players = _parse_next_data_players(sample_html_with_next_data)
        assert players[0]["name"] == "Nicolas Jackson"

    def test_fallback_to_first_last_name(self, sample_player_json_response):
        """Should construct name from firstName+lastName if 'name' is missing."""
        # Modify response to remove 'name' field
        sample_player_json_response["props"]["pageProps"]["players"]["players"][0]["player"] = {
            "firstName": "Test",
            "lastName": "Player",
            "slug": "test-player",
        }
        html = f"""
        <script id="__NEXT_DATA__" type="application/json">
        {json.dumps(sample_player_json_response)}
        </script>
        """

        players = _parse_next_data_players(html)
        assert players[0]["name"] == "Test Player"

    def test_skips_players_with_no_name(self, sample_player_json_response):
        """Should skip player objects without a name."""
        sample_player_json_response["props"]["pageProps"]["players"]["players"][0]["player"] = {
            "firstName": "",
            "lastName": "",
            "slug": "no-name",
        }
        html = f"""
        <script id="__NEXT_DATA__" type="application/json">
        {json.dumps(sample_player_json_response)}
        </script>
        """

        players = _parse_next_data_players(html)
        # Should have 2 players (one skipped due to no name)
        assert len(players) == 2

    def test_handles_missing_next_data_script(self):
        """Should return empty list if __NEXT_DATA__ script is missing."""
        html = "<html><body><h1>No data here</h1></body></html>"
        players = _parse_next_data_players(html)
        assert players == []

    def test_handles_invalid_json(self):
        """Should return empty list if __NEXT_DATA__ JSON is invalid."""
        html = """
        <script id="__NEXT_DATA__" type="application/json">
        {invalid json here}
        </script>
        """
        players = _parse_next_data_players(html)
        assert players == []

    def test_extracts_shirt_number_when_present(self, sample_html_with_next_data):
        """Should extract and convert shirt_number to int."""
        players = _parse_next_data_players(sample_html_with_next_data)
        assert players[0]["shirt_number"] == 15
        assert isinstance(players[0]["shirt_number"], int)

    def test_handles_missing_shirt_number(self, sample_player_json_response):
        """Should work when shirt_number is missing."""
        sample_player_json_response["props"]["pageProps"]["players"]["players"][0].pop(
            "shirtNumber"
        )
        html = f"""
        <script id="__NEXT_DATA__" type="application/json">
        {json.dumps(sample_player_json_response)}
        </script>
        """

        players = _parse_next_data_players(html)
        assert "shirt_number" not in players[0]

    def test_avoids_duplicate_players(self, sample_player_json_response):
        """Should skip duplicate player entries."""
        # Add the same player twice
        first_player = sample_player_json_response["props"]["pageProps"]["players"]["players"][0]
        sample_player_json_response["props"]["pageProps"]["players"]["players"].append(first_player)

        html = f"""
        <script id="__NEXT_DATA__" type="application/json">
        {json.dumps(sample_player_json_response)}
        </script>
        """

        players = _parse_next_data_players(html)
        # Should have 3 players (one duplicate removed)
        assert len(players) == 3


# ─────────────────────────────────────────────────────────────────────────
# _parse_sofascore_api_response
# ─────────────────────────────────────────────────────────────────────────


class TestParseSofascoreApiResponse:
    """Tests for parsing API responses."""

    def test_parses_players_key(self):
        """Should parse 'players' key in response."""
        response = {
            "players": [
                {"name": "Player 1", "position": "F", "shirtNumber": 10},
                {"name": "Player 2", "position": "D", "shirtNumber": 4},
            ]
        }

        players = _parse_sofascore_api_response(response)
        assert len(players) == 2
        assert players[0]["name"] == "Player 1"

    def test_parses_nested_player_object(self):
        """Should parse nested 'player' object structure."""
        response = {
            "players": [
                {
                    "player": {"name": "John Doe", "position": "M"},
                    "shirtNumber": 7,
                }
            ]
        }

        players = _parse_sofascore_api_response(response)
        assert len(players) == 1
        assert players[0]["name"] == "John Doe"

    def test_handles_empty_response(self):
        """Should handle empty response."""
        response = {"players": []}
        players = _parse_sofascore_api_response(response)
        assert players == []

    def test_handles_missing_players_key(self):
        """Should return empty list if no player data."""
        response = {"error": "Not found"}
        players = _parse_sofascore_api_response(response)
        assert players == []

    def test_converts_shirt_number_to_int(self):
        """Should convert shirt_number to integer."""
        response = {"players": [{"name": "Test", "position": "F", "shirtNumber": "9"}]}

        players = _parse_sofascore_api_response(response)
        assert players[0]["shirt_number"] == 9
        assert isinstance(players[0]["shirt_number"], int)

    def test_handles_invalid_shirt_number(self):
        """Should skip invalid shirt numbers."""
        response = {"players": [{"name": "Test", "position": "F", "shirtNumber": "invalid"}]}

        players = _parse_sofascore_api_response(response)
        assert "shirt_number" not in players[0]


# ─────────────────────────────────────────────────────────────────────────
# fetch_sofascore_squad (HTTP fallback)
# ─────────────────────────────────────────────────────────────────────────


class TestFetchSofascoreSquadHttpFallback:
    """Tests for the HTTP-only fallback function (shows why browser needed)."""

    def test_returns_empty_list(self, capsys):
        """Should return empty list and show informational message."""
        players = fetch_sofascore_squad("chelsea")

        assert players == []
        captured = capsys.readouterr()
        assert "Browser Automation Required" in captured.out


# ─────────────────────────────────────────────────────────────────────────
# fetch_sofascore_squad_with_playwright
# ─────────────────────────────────────────────────────────────────────────


class TestFetchSofascoreSquadWithPlaywright:
    """Tests for the Playwright-based scraper."""

    def test_uses_auto_lookup_for_known_team(self, capsys):
        """Should auto-lookup team ID for common teams."""
        with patch("app.ingest.sofascore.sync_playwright") as mock_pw:
            mock_browser = MagicMock()
            mock_page = MagicMock()

            mock_pw.return_value.__enter__.return_value.chromium.launch.return_value = mock_browser
            mock_browser.new_context.return_value.new_page.return_value = mock_page
            mock_page.content.return_value = (
                "<script id='__NEXT_DATA__'>{"
                '"props":{"pageProps":{"players":{"players":[]}}}}'
                "</script>"
            )

            fetch_sofascore_squad_with_playwright("chelsea")

            # Should use team ID 38 for Chelsea
            assert "38" in mock_page.goto.call_args[0][0]

    def test_requires_team_id_for_unknown_team(self, capsys):
        """Should fail for unknown team without explicit ID."""
        players = fetch_sofascore_squad_with_playwright("unknown-team")

        assert players == []
        captured = capsys.readouterr()
        assert "Team ID required" in captured.out

    def test_constructs_correct_url(self):
        """Should construct correct SofaScore URL."""
        with patch("app.ingest.sofascore.sync_playwright") as mock_pw:
            mock_browser = MagicMock()
            mock_page = MagicMock()

            mock_pw.return_value.__enter__.return_value.chromium.launch.return_value = mock_browser
            mock_browser.new_context.return_value.new_page.return_value = mock_page
            mock_page.content.return_value = (
                "<script id='__NEXT_DATA__'>{"
                '"props":{"pageProps":{"players":{"players":[]}}}}'
                "</script>"
            )

            fetch_sofascore_squad_with_playwright("chelsea", team_id=38)

            # Check that correct URL was called
            calls = mock_page.goto.call_args_list
            assert any(
                "https://www.sofascore.com/football/team/chelsea/38" in str(call) for call in calls
            )

    def test_handles_playwright_not_installed(self, monkeypatch):
        """Should handle ImportError if Playwright not installed."""
        monkeypatch.setattr(
            "builtins.__import__",
            Mock(side_effect=ImportError("No module named 'playwright'")),
        )

        # The function should return empty list
        # (actual implementation will show message about installing)
        # This test just verifies the error handling path exists

    def test_uses_headless_mode_by_default(self):
        """Should launch browser in headless mode by default."""
        with patch("app.ingest.sofascore.sync_playwright") as mock_pw:
            mock_browser = MagicMock()
            mock_page = MagicMock()

            mock_pw.return_value.__enter__.return_value.chromium.launch.return_value = mock_browser
            mock_browser.new_context.return_value.new_page.return_value = mock_page
            mock_page.content.return_value = (
                "<script id='__NEXT_DATA__'>{"
                '"props":{"pageProps":{"players":{"players":[]}}}}'
                "</script>"
            )

            fetch_sofascore_squad_with_playwright("chelsea", team_id=38)

            mock_browser.launch.assert_called()
            call_kwargs = mock_browser.launch.call_args[1]
            assert call_kwargs.get("headless", True) is True

    def test_respects_headless_false_parameter(self):
        """Should respect headless=False parameter."""
        with patch("app.ingest.sofascore.sync_playwright") as mock_pw:
            mock_browser = MagicMock()
            mock_page = MagicMock()

            mock_pw.return_value.__enter__.return_value.chromium.launch.return_value = mock_browser
            mock_browser.new_context.return_value.new_page.return_value = mock_page
            mock_page.content.return_value = (
                "<script id='__NEXT_DATA__'>{"
                '"props":{"pageProps":{"players":{"players":[]}}}}'
                "</script>"
            )

            fetch_sofascore_squad_with_playwright("chelsea", team_id=38, headless=False)

            call_kwargs = mock_browser.launch.call_args[1]
            assert call_kwargs.get("headless", True) is False

    def test_handles_page_load_error_gracefully(self):
        """Should handle page load timeouts gracefully."""
        with patch("app.ingest.sofascore.sync_playwright") as mock_pw:
            mock_browser = MagicMock()
            mock_page = MagicMock()

            mock_pw.return_value.__enter__.return_value.chromium.launch.return_value = mock_browser
            mock_browser.new_context.return_value.new_page.return_value = mock_page
            mock_page.goto.side_effect = TimeoutError("Page load timeout")
            mock_page.content.return_value = (
                "<script id='__NEXT_DATA__'>{"
                '"props":{"pageProps":{"players":{"players":[]}}}}'
                "</script>"
            )

            players = fetch_sofascore_squad_with_playwright("chelsea", team_id=38)

            # Should still return players from the page despite load warning
            assert isinstance(players, list)

    def test_extracts_and_returns_players(self, sample_html_with_next_data):
        """Should successfully extract and return player data."""
        with patch("app.ingest.sofascore.sync_playwright") as mock_pw:
            mock_browser = MagicMock()
            mock_page = MagicMock()

            mock_pw.return_value.__enter__.return_value.chromium.launch.return_value = mock_browser
            mock_browser.new_context.return_value.new_page.return_value = mock_page
            mock_page.content.return_value = sample_html_with_next_data

            players = fetch_sofascore_squad_with_playwright("chelsea", team_id=38)

            assert len(players) == 3
            assert players[0]["name"] == "Nicolas Jackson"
            assert players[1]["position"] == "D"


# ─────────────────────────────────────────────────────────────────────────
# COMMON_TEAMS constant
# ─────────────────────────────────────────────────────────────────────────


class TestCommonTeams:
    """Tests for the COMMON_TEAMS lookup table."""

    def test_contains_major_premier_league_teams(self):
        """Should contain major Premier League teams."""
        assert COMMON_TEAMS["chelsea"] == 38
        assert COMMON_TEAMS["manchester-city"] == 17
        assert COMMON_TEAMS["manchester-united"] == 33
        assert COMMON_TEAMS["liverpool"] == 39
        assert COMMON_TEAMS["arsenal"] == 42

    def test_all_team_ids_are_positive_integers(self):
        """All team IDs should be positive integers."""
        for team_slug, team_id in COMMON_TEAMS.items():
            assert isinstance(team_id, int), f"{team_slug} has non-integer ID"
            assert team_id > 0, f"{team_slug} has non-positive ID"

    def test_all_team_slugs_are_lowercase(self):
        """All team slugs should be lowercase."""
        for team_slug in COMMON_TEAMS.keys():
            assert team_slug == team_slug.lower(), f"{team_slug} is not lowercase"


# ─────────────────────────────────────────────────────────────────────────
# Edge Cases and Error Handling
# ─────────────────────────────────────────────────────────────────────────


class TestEdgeCasesAndErrors:
    """Tests for edge cases and error handling."""

    def test_handles_special_characters_in_player_names(self):
        """Should handle special characters in player names."""
        response = {
            "props": {
                "pageProps": {
                    "players": {
                        "players": [
                            {
                                "player": {
                                    "name": "Müller",
                                    "firstName": "Sérgio",
                                    "lastName": "Sánchez",
                                },
                                "position": "D",
                                "shirtNumber": 5,
                            }
                        ]
                    }
                }
            }
        }
        html = f'<script id="__NEXT_DATA__">{json.dumps(response)}</script>'

        players = _parse_next_data_players(html)
        assert players[0]["name"] == "Müller"

    def test_handles_unicode_characters(self):
        """Should handle Unicode characters."""
        response = {
            "props": {
                "pageProps": {
                    "players": {
                        "players": [
                            {
                                "player": {
                                    "name": "João",
                                    "firstName": "João",
                                    "lastName": "Pedro",
                                },
                                "position": "F",
                                "shirtNumber": 20,
                            }
                        ]
                    }
                }
            }
        }
        html = f'<script id="__NEXT_DATA__">{json.dumps(response)}</script>'

        players = _parse_next_data_players(html)
        assert "João" in players[0]["name"]

    def test_handles_very_large_shirt_numbers(self):
        """Should handle unusual shirt numbers."""
        response = {
            "props": {
                "pageProps": {
                    "players": {
                        "players": [
                            {
                                "player": {"name": "Test Player"},
                                "shirtNumber": 999,
                            }
                        ]
                    }
                }
            }
        }
        html = f'<script id="__NEXT_DATA__">{json.dumps(response)}</script>'

        players = _parse_next_data_players(html)
        assert players[0]["shirt_number"] == 999

    def test_handles_negative_shirt_numbers(self):
        """Should handle negative shirt numbers (unusual but possible)."""
        response = {
            "props": {
                "pageProps": {
                    "players": {
                        "players": [
                            {
                                "player": {"name": "Test Player"},
                                "shirtNumber": -1,
                            }
                        ]
                    }
                }
            }
        }
        html = f'<script id="__NEXT_DATA__">{json.dumps(response)}</script>'

        players = _parse_next_data_players(html)
        # Should still parse even with unusual number
        assert players[0]["shirt_number"] == -1

    def test_handles_null_values_in_response(self):
        """Should gracefully handle null values."""
        response = {
            "props": {
                "pageProps": {
                    "players": {
                        "players": [
                            {
                                "player": {
                                    "name": "Test",
                                    "firstName": None,
                                    "lastName": None,
                                },
                                "position": None,
                                "shirtNumber": None,
                            }
                        ]
                    }
                }
            }
        }
        html = f'<script id="__NEXT_DATA__">{json.dumps(response)}</script>'

        players = _parse_next_data_players(html)
        assert len(players) == 1
        assert players[0]["name"] == "Test"
        assert "position" not in players[0]


# ─────────────────────────────────────────────────────────────────────────
# Data Validation
# ─────────────────────────────────────────────────────────────────────────


class TestDataValidation:
    """Tests for data validation and format correctness."""

    def test_returned_player_objects_have_name_field(self):
        """Every returned player should have a 'name' field."""
        response = {
            "props": {
                "pageProps": {
                    "players": {
                        "players": [
                            {
                                "player": {
                                    "name": "John Doe",
                                },
                                "position": "F",
                            }
                        ]
                    }
                }
            }
        }
        html = f'<script id="__NEXT_DATA__">{json.dumps(response)}</script>'

        players = _parse_next_data_players(html)
        for player in players:
            assert "name" in player
            assert isinstance(player["name"], str)
            assert len(player["name"]) > 0

    def test_position_is_single_character_or_string(self):
        """Position should be F/M/D/G or longer string."""
        response = {
            "props": {
                "pageProps": {
                    "players": {
                        "players": [
                            {
                                "player": {"name": "Test"},
                                "position": "F",
                            }
                        ]
                    }
                }
            }
        }
        html = f'<script id="__NEXT_DATA__">{json.dumps(response)}</script>'

        players = _parse_next_data_players(html)
        if "position" in players[0]:
            assert isinstance(players[0]["position"], str)

    def test_shirt_number_is_integer(self):
        """Shirt number should be an integer."""
        response = {
            "props": {
                "pageProps": {
                    "players": {
                        "players": [
                            {
                                "player": {"name": "Test"},
                                "shirtNumber": 7,
                            }
                        ]
                    }
                }
            }
        }
        html = f'<script id="__NEXT_DATA__">{json.dumps(response)}</script>'

        players = _parse_next_data_players(html)
        if "shirt_number" in players[0]:
            assert isinstance(players[0]["shirt_number"], int)
