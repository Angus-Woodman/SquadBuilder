"""Integration tests for squad CRUD routes."""

from __future__ import annotations

from conftest import auth_header, create_player_in_db, register_user


def _setup_user_with_players(client, db, *, email="squad@example.com"):
    """Register a user and seed some players, return (token, [player_ids])."""
    data = register_user(client, email=email)
    token = data["access_token"]

    for i in range(1, 6):
        create_player_in_db(db, player_id=i, name=f"Player {i}")

    return token, [1, 2, 3, 4, 5]


# ── Create ────────────────────────────────────────────────────────────


class TestCreateSquad:
    def test_create_squad_success(self, client, db):
        token, pids = _setup_user_with_players(client, db)

        resp = client.post(
            "/squads/",
            json={"name": "My Squad", "player_ids": pids},
            headers=auth_header(token),
        )
        assert resp.status_code == 201
        body = resp.json()
        assert body["name"] == "My Squad"
        assert body["player_ids"] == pids
        assert "id" in body
        assert "created_at" in body

    def test_create_squad_empty_name(self, client, db):
        token, pids = _setup_user_with_players(client, db)

        resp = client.post(
            "/squads/",
            json={"name": "   ", "player_ids": pids},
            headers=auth_header(token),
        )
        assert resp.status_code == 400
        assert "name" in resp.json()["detail"].lower()

    def test_create_squad_no_players(self, client, db):
        token, _ = _setup_user_with_players(client, db)

        resp = client.post(
            "/squads/",
            json={"name": "Empty", "player_ids": []},
            headers=auth_header(token),
        )
        assert resp.status_code == 400
        assert "player" in resp.json()["detail"].lower()

    def test_create_squad_too_many_players(self, client, db):
        token, _ = _setup_user_with_players(client, db)

        # Seed 27 players
        for i in range(6, 28):
            create_player_in_db(db, player_id=i, name=f"Player {i}")

        resp = client.post(
            "/squads/",
            json={"name": "Too Big", "player_ids": list(range(1, 28))},
            headers=auth_header(token),
        )
        assert resp.status_code == 400
        assert "26" in resp.json()["detail"]

    def test_create_squad_unauthenticated(self, client):
        resp = client.post("/squads/", json={"name": "X", "player_ids": [1]})
        assert resp.status_code == 401


# ── List ──────────────────────────────────────────────────────────────


class TestListSquads:
    def test_list_squads_empty(self, client):
        token = register_user(client)["access_token"]
        resp = client.get("/squads/", headers=auth_header(token))
        assert resp.status_code == 200
        assert resp.json() == []

    def test_list_squads_returns_own_only(self, client, db):
        token_a, pids = _setup_user_with_players(client, db, email="a@example.com")
        token_b = register_user(client, email="b@example.com")["access_token"]

        # User A creates a squad
        client.post(
            "/squads/",
            json={"name": "A's Squad", "player_ids": pids[:3]},
            headers=auth_header(token_a),
        )

        # User B should see nothing
        resp = client.get("/squads/", headers=auth_header(token_b))
        assert resp.status_code == 200
        assert resp.json() == []

        # User A should see their squad
        resp = client.get("/squads/", headers=auth_header(token_a))
        assert len(resp.json()) == 1

    def test_list_squads_multiple(self, client, db):
        token, pids = _setup_user_with_players(client, db)

        client.post(
            "/squads/",
            json={"name": "First", "player_ids": pids[:2]},
            headers=auth_header(token),
        )
        client.post(
            "/squads/",
            json={"name": "Second", "player_ids": pids[2:4]},
            headers=auth_header(token),
        )

        resp = client.get("/squads/", headers=auth_header(token))
        assert len(resp.json()) == 2


# ── Get single squad ─────────────────────────────────────────────────


class TestGetSquad:
    def test_get_own_squad(self, client, db):
        token, pids = _setup_user_with_players(client, db)

        create_resp = client.post(
            "/squads/",
            json={"name": "Test", "player_ids": pids[:3]},
            headers=auth_header(token),
        )
        squad_id = create_resp.json()["id"]

        resp = client.get(f"/squads/{squad_id}", headers=auth_header(token))
        assert resp.status_code == 200
        body = resp.json()
        assert body["name"] == "Test"
        assert "players" in body  # full player details
        assert "owner_name" in body

    def test_get_nonexistent_squad(self, client):
        token = register_user(client)["access_token"]
        resp = client.get("/squads/99999", headers=auth_header(token))
        assert resp.status_code == 404

    def test_get_other_users_squad_denied(self, client, db):
        token_a, pids = _setup_user_with_players(client, db, email="own@example.com")
        token_b = register_user(client, email="other@example.com")["access_token"]

        create_resp = client.post(
            "/squads/",
            json={"name": "Private", "player_ids": pids[:2]},
            headers=auth_header(token_a),
        )
        squad_id = create_resp.json()["id"]

        # User B cannot see User A's squad (not friends)
        resp = client.get(f"/squads/{squad_id}", headers=auth_header(token_b))
        assert resp.status_code == 404

    def test_get_friend_squad_allowed(self, client, db):
        """An accepted friend can view the other user's squad."""
        token_a, pids = _setup_user_with_players(client, db, email="alice@example.com")
        token_b = register_user(client, email="bob@example.com")["access_token"]

        # Alice creates a squad
        create_resp = client.post(
            "/squads/",
            json={"name": "Alice Squad", "player_ids": pids[:2]},
            headers=auth_header(token_a),
        )
        squad_id = create_resp.json()["id"]

        # Alice sends friend request to Bob
        client.post(
            "/friends/request",
            json={"email": "bob@example.com"},
            headers=auth_header(token_a),
        )

        # Bob accepts
        friends_resp = client.get("/friends/", headers=auth_header(token_b))
        friendship_id = friends_resp.json()[0]["friendship_id"]
        client.put(f"/friends/{friendship_id}/accept", headers=auth_header(token_b))

        # Bob can now view Alice's squad
        resp = client.get(f"/squads/{squad_id}", headers=auth_header(token_b))
        assert resp.status_code == 200
        assert resp.json()["name"] == "Alice Squad"


# ── Update ────────────────────────────────────────────────────────────


class TestUpdateSquad:
    def test_update_squad_success(self, client, db):
        token, pids = _setup_user_with_players(client, db)

        create_resp = client.post(
            "/squads/",
            json={"name": "Original", "player_ids": pids[:2]},
            headers=auth_header(token),
        )
        squad_id = create_resp.json()["id"]

        resp = client.put(
            f"/squads/{squad_id}",
            json={"name": "Updated", "player_ids": pids[:4]},
            headers=auth_header(token),
        )
        assert resp.status_code == 200
        assert resp.json()["name"] == "Updated"
        assert resp.json()["player_ids"] == pids[:4]

    def test_update_other_users_squad(self, client, db):
        token_a, pids = _setup_user_with_players(client, db, email="upd_a@example.com")
        token_b = register_user(client, email="upd_b@example.com")["access_token"]

        create_resp = client.post(
            "/squads/",
            json={"name": "A's Squad", "player_ids": pids[:2]},
            headers=auth_header(token_a),
        )
        squad_id = create_resp.json()["id"]

        resp = client.put(
            f"/squads/{squad_id}",
            json={"name": "Hacked", "player_ids": pids[:2]},
            headers=auth_header(token_b),
        )
        assert resp.status_code == 404

    def test_update_squad_validation(self, client, db):
        token, pids = _setup_user_with_players(client, db)

        create_resp = client.post(
            "/squads/",
            json={"name": "Val", "player_ids": pids[:2]},
            headers=auth_header(token),
        )
        squad_id = create_resp.json()["id"]

        # Empty name
        resp = client.put(
            f"/squads/{squad_id}",
            json={"name": "  ", "player_ids": pids[:2]},
            headers=auth_header(token),
        )
        assert resp.status_code == 400


# ── Delete ────────────────────────────────────────────────────────────


class TestDeleteSquad:
    def test_delete_squad_success(self, client, db):
        token, pids = _setup_user_with_players(client, db)

        create_resp = client.post(
            "/squads/",
            json={"name": "Delete Me", "player_ids": pids[:2]},
            headers=auth_header(token),
        )
        squad_id = create_resp.json()["id"]

        resp = client.delete(f"/squads/{squad_id}", headers=auth_header(token))
        assert resp.status_code == 204

        # Verify it's gone
        resp = client.get("/squads/", headers=auth_header(token))
        assert len(resp.json()) == 0

    def test_delete_other_users_squad(self, client, db):
        token_a, pids = _setup_user_with_players(client, db, email="del_a@example.com")
        token_b = register_user(client, email="del_b@example.com")["access_token"]

        create_resp = client.post(
            "/squads/",
            json={"name": "A's Squad", "player_ids": pids[:2]},
            headers=auth_header(token_a),
        )
        squad_id = create_resp.json()["id"]

        resp = client.delete(f"/squads/{squad_id}", headers=auth_header(token_b))
        assert resp.status_code == 404

    def test_delete_nonexistent_squad(self, client):
        token = register_user(client)["access_token"]
        resp = client.delete("/squads/99999", headers=auth_header(token))
        assert resp.status_code == 404
