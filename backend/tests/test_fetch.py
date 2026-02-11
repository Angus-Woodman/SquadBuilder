import pytest
import requests

from app.ingest.fetch import fetch_teams_from_league


class DummyResponse:
    def __init__(self, status_code=200, json_data=None, text="OK", reason="OK"):
        self.status_code = status_code
        self._json_data = json_data or {}
        self.text = text
        self.reason = reason

    def json(self):
        return self._json_data

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(f"{self.status_code} {self.reason}")


def test_fetch_success(monkeypatch):
    monkeypatch.setenv("FOOTBALL_DATA_API_TOKEN", "test-token")

    def fake_get(url, headers=None, timeout=None):
        assert headers["X-Auth-Token"] == "test-token"
        assert timeout == 30
        assert "PL" in url

        return DummyResponse(json_data={"teams": [{"id": 1, "name": "Arsenal"}]})

    monkeypatch.setattr(requests, "get", fake_get)

    data = fetch_teams_from_league(" pl ")

    assert "teams" in data
    assert data["teams"][0]["name"] == "Arsenal"


def test_missing_token_raises(monkeypatch):
    monkeypatch.delenv("FOOTBALL_DATA_API_TOKEN", raising=False)

    with pytest.raises(RuntimeError, match="Missing FOOTBALL_DATA_API_TOKEN"):
        fetch_teams_from_league("PL")


def test_http_error_raises(monkeypatch):
    monkeypatch.setenv("FOOTBALL_DATA_API_TOKEN", "test-token")

    def fake_get(url, headers=None, timeout=None):
        return DummyResponse(
            status_code=403,
            text="Forbidden",
            reason="Forbidden",
        )

    monkeypatch.setattr(requests, "get", fake_get)

    with pytest.raises(RuntimeError, match="Request failed: 403"):
        fetch_teams_from_league("PL")
