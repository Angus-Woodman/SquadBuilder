"""Integration tests for public player endpoints and the health check."""

from __future__ import annotations

from datetime import date

from conftest import auth_header, create_player_in_db, make_admin, register_user

# ── Health ────────────────────────────────────────────────────────────


class TestHealth:
    def test_health_returns_ok(self, client):
        resp = client.get("/api/health")
        assert resp.status_code == 200
        assert resp.json() == {"status": "ok"}


# ── GET /players ──────────────────────────────────────────────────────


class TestGetPlayers:
    def test_get_players_empty_db(self, client):
        resp = client.get("/api/players")
        assert resp.status_code == 200
        body = resp.json()
        assert body["count"] == 0
        assert body["players"] == []

    def test_get_players_returns_data(self, client, db):
        create_player_in_db(db, player_id=1, name="Harry Kane", nationality="England")
        create_player_in_db(db, player_id=2, name="Jude Bellingham", nationality="England")

        resp = client.get("/api/players")
        assert resp.status_code == 200
        body = resp.json()
        assert body["count"] == 2
        names = {p["name"] for p in body["players"]}
        assert "Harry Kane" in names
        assert "Jude Bellingham" in names

    def test_get_players_includes_all_fields(self, client, db):
        create_player_in_db(
            db,
            player_id=10,
            name="Test Player",
            position="Forward",
            nationality="England",
            date_of_birth=date(1995, 6, 15),
        )

        resp = client.get("/api/players")
        player = resp.json()["players"][0]
        assert player["player_id"] == 10
        assert player["name"] == "Test Player"
        assert player["position"] == "Forward"
        assert player["nationality"] == "England"
        assert player["date_of_birth"] == "1995-06-15"

    def test_get_players_filter_nationality(self, client, db):
        create_player_in_db(db, player_id=1, name="English", nationality="England")
        create_player_in_db(db, player_id=2, name="French", nationality="France")

        resp = client.get("/api/players?nationality=England")
        body = resp.json()
        assert body["count"] == 1
        assert body["players"][0]["name"] == "English"

    def test_get_players_nationality_case_insensitive(self, client, db):
        create_player_in_db(db, player_id=1, name="English", nationality="England")

        resp = client.get("/api/players?nationality=england")
        assert resp.json()["count"] == 1

    def test_get_players_limit(self, client, db):
        for i in range(1, 11):
            create_player_in_db(db, player_id=i, name=f"Player {i}")

        resp = client.get("/api/players?limit=5")
        assert resp.json()["count"] == 5

    def test_get_players_invalid_limit_zero(self, client):
        resp = client.get("/api/players?limit=0")
        assert resp.status_code == 400

    def test_get_players_invalid_limit_too_high(self, client):
        resp = client.get("/api/players?limit=3000")
        assert resp.status_code == 400


# ── GET /suggested (public) ───────────────────────────────────────────


class TestGetSuggestedPublic:
    def test_suggested_empty(self, client):
        resp = client.get("/api/suggested")
        assert resp.status_code == 200
        assert resp.json()["player_ids"] == []

    def test_suggested_returns_ids(self, client, db):
        """Set suggested via admin, then verify public endpoint returns them."""
        # Seed players and create admin
        create_player_in_db(db, player_id=10, name="Kane")
        create_player_in_db(db, player_id=20, name="Bellingham")

        admin_data = register_user(client, email="adm@example.com")
        me = client.get("/api/auth/me", headers=auth_header(admin_data["access_token"])).json()
        make_admin(db, me["id"])
        admin_token = client.post(
            "/api/auth/login",
            json={"email": "adm@example.com", "password": "password123"},
        ).json()["access_token"]

        # Admin sets suggested
        client.put(
            "/api/admin/suggested",
            json={"player_ids": [10, 20]},
            headers=auth_header(admin_token),
        )

        # Public endpoint (no auth)
        resp = client.get("/api/suggested")
        assert resp.status_code == 200
        ids = resp.json()["player_ids"]
        assert 10 in ids
        assert 20 in ids

    def test_suggested_no_auth_required(self, client):
        """The /suggested endpoint should work without authentication."""
        resp = client.get("/api/suggested")
        assert resp.status_code == 200
