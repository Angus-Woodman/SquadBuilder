"""Integration tests for admin-only routes (suggested players, users, player edits)."""

from __future__ import annotations

from conftest import auth_header, create_player_in_db, make_admin, register_user


def _admin_token(client, db, *, email="admin@example.com") -> str:
    """Register a user, promote to admin, return their token."""
    data = register_user(client, email=email, display_name="Admin")
    token = data["access_token"]
    # Get user ID from /auth/me
    me = client.get("/api/auth/me", headers=auth_header(token)).json()
    make_admin(db, me["id"])

    # Re-login to get a fresh token with the admin role
    resp = client.post(
        "/api/auth/login",
        json={"email": email, "password": "password123"},
    )
    return resp.json()["access_token"]


def _regular_token(client, *, email="user@example.com") -> str:
    return register_user(client, email=email)["access_token"]


# ── Suggested players ─────────────────────────────────────────────────


class TestSuggested:
    def test_get_suggested_empty(self, client, db):
        token = _admin_token(client, db)
        resp = client.get("/api/admin/suggested", headers=auth_header(token))
        assert resp.status_code == 200
        assert resp.json() == []

    def test_set_and_get_suggested(self, client, db):
        token = _admin_token(client, db)

        # Seed players
        create_player_in_db(db, player_id=10, name="Harry Kane")
        create_player_in_db(db, player_id=20, name="Jude Bellingham")

        # Set suggested
        resp = client.put(
            "/api/admin/suggested",
            json={"player_ids": [10, 20]},
            headers=auth_header(token),
        )
        assert resp.status_code == 200
        assert resp.json()["count"] == 2

        # Get suggested
        resp = client.get("/api/admin/suggested", headers=auth_header(token))
        assert resp.status_code == 200
        suggested = resp.json()
        assert len(suggested) == 2
        names = {s["name"] for s in suggested}
        assert "Harry Kane" in names
        assert "Jude Bellingham" in names

    def test_set_suggested_replaces_previous(self, client, db):
        token = _admin_token(client, db)

        create_player_in_db(db, player_id=10, name="Player A")
        create_player_in_db(db, player_id=20, name="Player B")
        create_player_in_db(db, player_id=30, name="Player C")

        client.put(
            "/api/admin/suggested",
            json={"player_ids": [10, 20]},
            headers=auth_header(token),
        )
        client.put(
            "/api/admin/suggested",
            json={"player_ids": [30]},
            headers=auth_header(token),
        )

        suggested = client.get("/api/admin/suggested", headers=auth_header(token)).json()
        assert len(suggested) == 1
        assert suggested[0]["name"] == "Player C"

    def test_suggested_non_admin_forbidden(self, client, db):
        token = _regular_token(client)
        resp = client.get("/api/admin/suggested", headers=auth_header(token))
        assert resp.status_code == 403


# ── User management ──────────────────────────────────────────────────


class TestUserManagement:
    def test_list_users(self, client, db):
        token = _admin_token(client, db)
        register_user(client, email="other@example.com")

        resp = client.get("/api/admin/users", headers=auth_header(token))
        assert resp.status_code == 200
        users = resp.json()
        assert len(users) >= 2  # admin + other
        emails = {u["email"] for u in users}
        assert "admin@example.com" in emails
        assert "other@example.com" in emails

    def test_create_user(self, client, db):
        token = _admin_token(client, db)

        resp = client.post(
            "/api/admin/users",
            json={
                "email": "created@example.com",
                "display_name": "Created User",
                "password": "pass1234",
                "role": "user",
            },
            headers=auth_header(token),
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["email"] == "created@example.com"
        assert body["role"] == "user"

    def test_create_user_duplicate_email(self, client, db):
        token = _admin_token(client, db)

        client.post(
            "/api/admin/users",
            json={
                "email": "dup@example.com",
                "display_name": "First",
                "password": "pass1234",
            },
            headers=auth_header(token),
        )
        resp = client.post(
            "/api/admin/users",
            json={
                "email": "dup@example.com",
                "display_name": "Second",
                "password": "pass1234",
            },
            headers=auth_header(token),
        )
        assert resp.status_code == 409

    def test_create_user_invalid_role(self, client, db):
        token = _admin_token(client, db)

        resp = client.post(
            "/api/admin/users",
            json={
                "email": "bad@example.com",
                "display_name": "Bad Role",
                "password": "pass1234",
                "role": "superadmin",
            },
            headers=auth_header(token),
        )
        assert resp.status_code == 400

    def test_delete_user(self, client, db):
        token = _admin_token(client, db)

        # Create a target user
        resp = client.post(
            "/api/admin/users",
            json={
                "email": "target@example.com",
                "display_name": "Target",
                "password": "pass1234",
            },
            headers=auth_header(token),
        )
        target_id = resp.json()["id"]

        resp = client.delete(f"/api/admin/users/{target_id}", headers=auth_header(token))
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"

    def test_delete_self_forbidden(self, client, db):
        token = _admin_token(client, db)
        me = client.get("/api/auth/me", headers=auth_header(token)).json()

        resp = client.delete(f"/api/admin/users/{me['id']}", headers=auth_header(token))
        assert resp.status_code == 400
        assert "own account" in resp.json()["detail"].lower()

    def test_delete_nonexistent_user(self, client, db):
        token = _admin_token(client, db)
        resp = client.delete("/api/admin/users/99999", headers=auth_header(token))
        assert resp.status_code == 404

    def test_set_user_role(self, client, db):
        token = _admin_token(client, db)

        # Create a regular user
        resp = client.post(
            "/api/admin/users",
            json={
                "email": "promote@example.com",
                "display_name": "Promotable",
                "password": "pass1234",
            },
            headers=auth_header(token),
        )
        user_id = resp.json()["id"]

        # Promote to admin
        resp = client.put(
            f"/api/admin/users/{user_id}/role?role=admin",
            headers=auth_header(token),
        )
        assert resp.status_code == 200
        assert resp.json()["role"] == "admin"

        # Demote back
        resp = client.put(
            f"/api/admin/users/{user_id}/role?role=user",
            headers=auth_header(token),
        )
        assert resp.json()["role"] == "user"

    def test_set_user_role_invalid(self, client, db):
        token = _admin_token(client, db)

        resp = client.post(
            "/api/admin/users",
            json={
                "email": "badrole@example.com",
                "display_name": "Bad",
                "password": "pass1234",
            },
            headers=auth_header(token),
        )
        user_id = resp.json()["id"]

        resp = client.put(
            f"/api/admin/users/{user_id}/role?role=superadmin",
            headers=auth_header(token),
        )
        assert resp.status_code == 400

    def test_non_admin_cannot_list_users(self, client):
        token = _regular_token(client)
        resp = client.get("/api/admin/users", headers=auth_header(token))
        assert resp.status_code == 403


# ── Player search & edit ─────────────────────────────────────────────


class TestPlayerManagement:
    def test_search_players(self, client, db):
        token = _admin_token(client, db)

        create_player_in_db(db, player_id=1, name="Harry Kane")
        create_player_in_db(db, player_id=2, name="Harry Maguire")
        create_player_in_db(db, player_id=3, name="Jude Bellingham")

        resp = client.get(
            "/api/admin/players/search?q=Harry",
            headers=auth_header(token),
        )
        assert resp.status_code == 200
        results = resp.json()
        assert len(results) == 2
        names = {p["name"] for p in results}
        assert "Harry Kane" in names
        assert "Harry Maguire" in names

    def test_search_players_empty_query(self, client, db):
        token = _admin_token(client, db)

        create_player_in_db(db, player_id=1, name="Some Player")

        resp = client.get("/api/admin/players/search?q=", headers=auth_header(token))
        assert resp.status_code == 200
        assert len(resp.json()) >= 1

    def test_update_player(self, client, db):
        token = _admin_token(client, db)

        create_player_in_db(db, player_id=100, name="Old Name", position="Forward")

        resp = client.put(
            "/api/admin/players/100",
            json={"name": "New Name", "position": "Midfielder"},
            headers=auth_header(token),
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["name"] == "New Name"
        assert body["position"] == "Midfielder"

    def test_update_player_partial(self, client, db):
        """Only update the fields that are provided."""
        token = _admin_token(client, db)

        create_player_in_db(
            db, player_id=101, name="Keep Name", position="Goalkeeper", nationality="England"
        )

        resp = client.put(
            "/api/admin/players/101",
            json={"position": "Defender"},
            headers=auth_header(token),
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["name"] == "Keep Name"  # unchanged
        assert body["position"] == "Defender"  # changed
        assert body["nationality"] == "England"  # unchanged

    def test_update_player_invalid_date(self, client, db):
        token = _admin_token(client, db)

        create_player_in_db(db, player_id=102, name="Date Test")

        resp = client.put(
            "/api/admin/players/102",
            json={"date_of_birth": "not-a-date"},
            headers=auth_header(token),
        )
        assert resp.status_code == 400
        assert "date" in resp.json()["detail"].lower()

    def test_update_nonexistent_player(self, client, db):
        token = _admin_token(client, db)

        resp = client.put(
            "/api/admin/players/99999",
            json={"name": "Ghost"},
            headers=auth_header(token),
        )
        assert resp.status_code == 404
