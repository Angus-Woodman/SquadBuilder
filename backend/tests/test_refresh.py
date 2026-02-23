"""Integration tests for the POST /api/refresh endpoint (admin-only data refresh)."""

from __future__ import annotations

from unittest.mock import patch

from conftest import auth_header, make_admin, register_user


def _admin_token(client, db, *, email="refresh_admin@example.com") -> str:
    """Register a user, promote to admin, return a fresh admin token."""
    data = register_user(client, email=email)
    me = client.get("/api/auth/me", headers=auth_header(data["access_token"])).json()
    make_admin(db, me["id"])
    resp = client.post(
        "/api/auth/login",
        json={"email": email, "password": "password123"},
    )
    return resp.json()["access_token"]


class TestRefreshEndpoint:
    def test_refresh_requires_admin(self, client):
        """Non-admin users should be rejected."""
        token = register_user(client)["access_token"]
        resp = client.post(
            "/api/refresh",
            json={"competition": ["PL"]},
            headers=auth_header(token),
        )
        assert resp.status_code == 403

    def test_refresh_unauthenticated(self, client):
        """Unauthenticated requests should be rejected."""
        resp = client.post("/api/refresh", json={"competition": ["PL"]})
        assert resp.status_code == 401

    @patch("app.ingest.fetch.fetch_teams_from_league")
    @patch("app.db.store.upsert_players")
    def test_refresh_success(self, mock_upsert, mock_fetch, client, db):
        """Admin can trigger a refresh with mocked external calls."""
        token = _admin_token(client, db)

        # Mock the external API to return a minimal valid payload
        mock_fetch.return_value = {
            "teams": [
                {
                    "id": 1,
                    "name": "Test FC",
                    "squad": [
                        {
                            "id": 100,
                            "name": "Test Player",
                            "position": "Forward",
                            "nationality": "England",
                        },
                    ],
                }
            ]
        }
        mock_upsert.return_value = None

        resp = client.post(
            "/api/refresh",
            json={"competition": ["PL"]},
            headers=auth_header(token),
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["competition"] == ["PL"]
        assert body["processed_players"] >= 1
        mock_fetch.assert_called_once_with("PL")
        mock_upsert.assert_called_once()
