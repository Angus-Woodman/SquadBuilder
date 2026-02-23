"""Integration tests for authentication API routes (register, login, /auth/me)."""

from __future__ import annotations

from conftest import auth_header, register_user

# ── Registration ──────────────────────────────────────────────────────


class TestRegister:
    def test_register_success(self, client):
        resp = client.post(
            "/auth/register",
            json={
                "email": "new@example.com",
                "display_name": "New User",
                "password": "secret123",
            },
        )
        assert resp.status_code == 201
        data = resp.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"

    def test_register_returns_valid_token(self, client):
        data = register_user(client, email="tok@example.com")
        token = data["access_token"]

        me = client.get("/auth/me", headers=auth_header(token))
        assert me.status_code == 200
        assert me.json()["email"] == "tok@example.com"

    def test_register_duplicate_email(self, client):
        register_user(client, email="dup@example.com")
        resp = client.post(
            "/auth/register",
            json={
                "email": "dup@example.com",
                "display_name": "Dup",
                "password": "secret123",
            },
        )
        assert resp.status_code == 409
        assert "already registered" in resp.json()["detail"].lower()

    def test_register_duplicate_email_case_insensitive(self, client):
        register_user(client, email="case@example.com")
        resp = client.post(
            "/auth/register",
            json={
                "email": "CASE@example.com",
                "display_name": "Case",
                "password": "secret123",
            },
        )
        assert resp.status_code == 409

    def test_register_short_password(self, client):
        resp = client.post(
            "/auth/register",
            json={
                "email": "short@example.com",
                "display_name": "Short",
                "password": "abc",
            },
        )
        assert resp.status_code == 400
        assert "6 characters" in resp.json()["detail"]

    def test_register_invalid_email(self, client):
        resp = client.post(
            "/auth/register",
            json={
                "email": "not-an-email",
                "display_name": "Bad",
                "password": "secret123",
            },
        )
        assert resp.status_code == 422  # Pydantic validation

    def test_register_strips_display_name(self, client):
        data = register_user(client, email="strip@example.com", display_name="  Padded  ")
        token = data["access_token"]

        me = client.get("/auth/me", headers=auth_header(token))
        assert me.json()["display_name"] == "Padded"


# ── Login ─────────────────────────────────────────────────────────────


class TestLogin:
    def test_login_success(self, client):
        register_user(client, email="login@example.com", password="mypass123")

        resp = client.post(
            "/auth/login",
            json={"email": "login@example.com", "password": "mypass123"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"

    def test_login_wrong_password(self, client):
        register_user(client, email="wrong@example.com", password="correct")

        resp = client.post(
            "/auth/login",
            json={"email": "wrong@example.com", "password": "incorrect"},
        )
        assert resp.status_code == 401
        assert "invalid" in resp.json()["detail"].lower()

    def test_login_nonexistent_email(self, client):
        resp = client.post(
            "/auth/login",
            json={"email": "ghost@example.com", "password": "whatever"},
        )
        assert resp.status_code == 401

    def test_login_case_insensitive_email(self, client):
        register_user(client, email="ci@example.com", password="pass123456")

        resp = client.post(
            "/auth/login",
            json={"email": "CI@EXAMPLE.COM", "password": "pass123456"},
        )
        assert resp.status_code == 200


# ── /auth/me ──────────────────────────────────────────────────────────


class TestMe:
    def test_me_returns_user_info(self, client):
        data = register_user(
            client,
            email="me@example.com",
            display_name="Me User",
        )
        resp = client.get("/auth/me", headers=auth_header(data["access_token"]))
        assert resp.status_code == 200
        body = resp.json()
        assert body["email"] == "me@example.com"
        assert body["display_name"] == "Me User"
        assert body["role"] == "user"
        assert "id" in body
        assert "created_at" in body

    def test_me_unauthenticated(self, client):
        resp = client.get("/auth/me")
        assert resp.status_code == 401

    def test_me_invalid_token(self, client):
        resp = client.get("/auth/me", headers=auth_header("invalid.jwt.token"))
        assert resp.status_code == 401
