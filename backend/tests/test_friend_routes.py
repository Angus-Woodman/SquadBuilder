"""Integration tests for friend routes (request, accept, remove, list, squads)."""

from __future__ import annotations

from conftest import auth_header, create_player_in_db, register_user


def _two_users(client) -> tuple[str, str]:
    """Register two users and return their tokens."""
    token_a = register_user(client, email="alice@example.com", display_name="Alice")["access_token"]
    token_b = register_user(client, email="bob@example.com", display_name="Bob")["access_token"]
    return token_a, token_b


def _befriend(client, token_a: str, token_b: str) -> int:
    """A sends request to B, B accepts. Returns friendship_id."""
    client.post(
        "/api/friends/request",
        json={"email": "bob@example.com"},
        headers=auth_header(token_a),
    )
    friends = client.get("/api/friends/", headers=auth_header(token_b)).json()
    fid = friends[0]["friendship_id"]
    client.put(f"/api/friends/{fid}/accept", headers=auth_header(token_b))
    return fid


# ── Send friend request ──────────────────────────────────────────────


class TestSendRequest:
    def test_send_request_success(self, client):
        token_a, token_b = _two_users(client)

        resp = client.post(
            "/api/friends/request",
            json={"email": "bob@example.com"},
            headers=auth_header(token_a),
        )
        assert resp.status_code == 201
        body = resp.json()
        assert body["display_name"] == "Bob"
        assert body["status"] == "pending"
        assert body["direction"] == "sent"

    def test_send_request_to_self(self, client):
        token = register_user(client, email="self@example.com")["access_token"]

        resp = client.post(
            "/api/friends/request",
            json={"email": "self@example.com"},
            headers=auth_header(token),
        )
        assert resp.status_code == 400
        assert "yourself" in resp.json()["detail"].lower()

    def test_send_request_duplicate(self, client):
        token_a, _ = _two_users(client)

        client.post(
            "/api/friends/request",
            json={"email": "bob@example.com"},
            headers=auth_header(token_a),
        )
        resp = client.post(
            "/api/friends/request",
            json={"email": "bob@example.com"},
            headers=auth_header(token_a),
        )
        assert resp.status_code == 409
        assert "already exists" in resp.json()["detail"].lower()

    def test_send_request_reverse_duplicate(self, client):
        """If A→B exists, B→A should also be rejected."""
        token_a, token_b = _two_users(client)

        client.post(
            "/api/friends/request",
            json={"email": "bob@example.com"},
            headers=auth_header(token_a),
        )
        resp = client.post(
            "/api/friends/request",
            json={"email": "alice@example.com"},
            headers=auth_header(token_b),
        )
        assert resp.status_code == 409

    def test_send_request_nonexistent_user(self, client):
        token = register_user(client, email="lonely@example.com")["access_token"]

        resp = client.post(
            "/api/friends/request",
            json={"email": "ghost@example.com"},
            headers=auth_header(token),
        )
        assert resp.status_code == 404


# ── Accept friend request ────────────────────────────────────────────


class TestAcceptRequest:
    def test_accept_success(self, client):
        token_a, token_b = _two_users(client)

        # Alice → Bob
        client.post(
            "/api/friends/request",
            json={"email": "bob@example.com"},
            headers=auth_header(token_a),
        )

        # Bob sees the request
        friends = client.get("/api/friends/", headers=auth_header(token_b)).json()
        assert len(friends) == 1
        fid = friends[0]["friendship_id"]
        assert friends[0]["status"] == "pending"
        assert friends[0]["direction"] == "received"

        # Bob accepts
        resp = client.put(f"/api/friends/{fid}/accept", headers=auth_header(token_b))
        assert resp.status_code == 200
        assert resp.json()["status"] == "accepted"

    def test_only_addressee_can_accept(self, client):
        """The sender (Alice) should not be able to accept their own request."""
        token_a, token_b = _two_users(client)

        resp = client.post(
            "/api/friends/request",
            json={"email": "bob@example.com"},
            headers=auth_header(token_a),
        )
        fid = resp.json()["friendship_id"]

        # Alice tries to accept her own request
        resp = client.put(f"/api/friends/{fid}/accept", headers=auth_header(token_a))
        assert resp.status_code == 404

    def test_accept_nonexistent_request(self, client):
        token = register_user(client)["access_token"]
        resp = client.put("/api/friends/99999/accept", headers=auth_header(token))
        assert resp.status_code == 404

    def test_accept_already_accepted(self, client):
        token_a, token_b = _two_users(client)
        fid = _befriend(client, token_a, token_b)

        # Try to accept again
        resp = client.put(f"/api/friends/{fid}/accept", headers=auth_header(token_b))
        assert resp.status_code == 404  # not pending anymore


# ── List friends ──────────────────────────────────────────────────────


class TestListFriends:
    def test_list_friends_empty(self, client):
        token = register_user(client)["access_token"]
        resp = client.get("/api/friends/", headers=auth_header(token))
        assert resp.status_code == 200
        assert resp.json() == []

    def test_list_friends_both_sides(self, client):
        token_a, token_b = _two_users(client)
        _befriend(client, token_a, token_b)

        # Alice sees Bob
        friends_a = client.get("/api/friends/", headers=auth_header(token_a)).json()
        assert len(friends_a) == 1
        assert friends_a[0]["display_name"] == "Bob"

        # Bob sees Alice
        friends_b = client.get("/api/friends/", headers=auth_header(token_b)).json()
        assert len(friends_b) == 1
        assert friends_b[0]["display_name"] == "Alice"

    def test_list_includes_pending(self, client):
        token_a, token_b = _two_users(client)

        client.post(
            "/api/friends/request",
            json={"email": "bob@example.com"},
            headers=auth_header(token_a),
        )

        friends_a = client.get("/api/friends/", headers=auth_header(token_a)).json()
        assert len(friends_a) == 1
        assert friends_a[0]["status"] == "pending"


# ── Remove friend ────────────────────────────────────────────────────


class TestRemoveFriend:
    def test_remove_accepted_friend(self, client):
        token_a, token_b = _two_users(client)
        fid = _befriend(client, token_a, token_b)

        resp = client.delete(f"/api/friends/{fid}", headers=auth_header(token_a))
        assert resp.status_code == 204

        # Verify both sides see empty
        assert client.get("/api/friends/", headers=auth_header(token_a)).json() == []
        assert client.get("/api/friends/", headers=auth_header(token_b)).json() == []

    def test_remove_pending_request(self, client):
        token_a, token_b = _two_users(client)

        resp = client.post(
            "/api/friends/request",
            json={"email": "bob@example.com"},
            headers=auth_header(token_a),
        )
        fid = resp.json()["friendship_id"]

        # Either side can remove
        resp = client.delete(f"/api/friends/{fid}", headers=auth_header(token_b))
        assert resp.status_code == 204

    def test_remove_nonexistent_friendship(self, client):
        token = register_user(client)["access_token"]
        resp = client.delete("/api/friends/99999", headers=auth_header(token))
        assert resp.status_code == 404

    def test_remove_others_friendship(self, client):
        """A third party cannot remove someone else's friendship."""
        token_a, token_b = _two_users(client)
        fid = _befriend(client, token_a, token_b)

        token_c = register_user(client, email="carol@example.com")["access_token"]
        resp = client.delete(f"/api/friends/{fid}", headers=auth_header(token_c))
        assert resp.status_code == 404


# ── Friend squads ────────────────────────────────────────────────────


class TestFriendSquads:
    def test_view_friend_squads(self, client, db):
        token_a, token_b = _two_users(client)
        _befriend(client, token_a, token_b)

        # Alice creates a squad
        create_player_in_db(db, player_id=1, name="Player 1")
        create_player_in_db(db, player_id=2, name="Player 2")

        client.post(
            "/api/squads/",
            json={"name": "Alice's XI", "player_ids": [1, 2]},
            headers=auth_header(token_a),
        )

        # Get Alice's user ID
        alice_info = client.get("/api/auth/me", headers=auth_header(token_a)).json()
        alice_id = alice_info["id"]

        # Bob views Alice's squads
        resp = client.get(
            f"/api/friends/{alice_id}/squads",
            headers=auth_header(token_b),
        )
        assert resp.status_code == 200
        squads = resp.json()
        assert len(squads) == 1
        assert squads[0]["name"] == "Alice's XI"

    def test_view_squads_not_friends(self, client, db):
        token_a, token_b = _two_users(client)  # not befriended

        alice_info = client.get("/api/auth/me", headers=auth_header(token_a)).json()
        alice_id = alice_info["id"]

        resp = client.get(
            f"/api/friends/{alice_id}/squads",
            headers=auth_header(token_b),
        )
        assert resp.status_code == 403

    def test_view_squads_pending_friendship(self, client, db):
        """Pending (not accepted) friendship should not grant access."""
        token_a, token_b = _two_users(client)

        # Send request but don't accept
        client.post(
            "/api/friends/request",
            json={"email": "bob@example.com"},
            headers=auth_header(token_a),
        )

        alice_info = client.get("/api/auth/me", headers=auth_header(token_a)).json()
        resp = client.get(
            f"/api/friends/{alice_info['id']}/squads",
            headers=auth_header(token_b),
        )
        assert resp.status_code == 403
