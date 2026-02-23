"""Unit tests for auth helpers (password hashing, JWT tokens).

These tests exercise the pure functions in ``app.auth`` and do NOT
require a running database.
"""

from __future__ import annotations

import os
from datetime import UTC, datetime, timedelta

import pytest

from app.auth import (
    _ALGORITHM,
    _get_secret_key,
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)
from app.db.models import UserRole

# ── Password hashing ──────────────────────────────────────────────────


class TestPasswordHashing:
    def test_hash_returns_bcrypt_string(self):
        h = hash_password("mysecret")
        assert h.startswith("$2b$") or h.startswith("$2a$")

    def test_verify_correct_password(self):
        h = hash_password("correct-horse")
        assert verify_password("correct-horse", h) is True

    def test_verify_wrong_password(self):
        h = hash_password("correct-horse")
        assert verify_password("wrong-horse", h) is False

    def test_different_passwords_produce_different_hashes(self):
        h1 = hash_password("aaa")
        h2 = hash_password("bbb")
        assert h1 != h2

    def test_same_password_produces_different_salts(self):
        h1 = hash_password("same")
        h2 = hash_password("same")
        # bcrypt uses a random salt, so hashes should differ
        assert h1 != h2
        # but both should verify
        assert verify_password("same", h1)
        assert verify_password("same", h2)


# ── JWT tokens ────────────────────────────────────────────────────────


class TestJWTTokens:
    def test_create_and_decode_roundtrip(self):
        token = create_access_token(42, UserRole.user)
        payload = decode_access_token(token)
        assert payload["sub"] == "42"
        assert payload["role"] == "user"

    def test_admin_role_in_token(self):
        token = create_access_token(1, UserRole.admin)
        payload = decode_access_token(token)
        assert payload["role"] == "admin"

    def test_token_contains_expiration(self):
        token = create_access_token(1, UserRole.user)
        payload = decode_access_token(token)
        assert "exp" in payload
        assert "iat" in payload

    def test_token_expiry_is_in_the_future(self):
        token = create_access_token(1, UserRole.user)
        payload = decode_access_token(token)
        exp = datetime.fromtimestamp(payload["exp"], tz=UTC)
        assert exp > datetime.now(UTC)

    def test_decode_with_wrong_secret_raises(self):
        from jose import jwt as jose_jwt
        from jose.exceptions import JWTError

        token = jose_jwt.encode(
            {"sub": "1", "role": "user", "exp": datetime.now(UTC) + timedelta(hours=1)},
            "wrong-secret",
            algorithm=_ALGORITHM,
        )
        with pytest.raises(JWTError):
            decode_access_token(token)

    def test_decode_expired_token_raises(self):
        from jose import jwt as jose_jwt
        from jose.exceptions import ExpiredSignatureError

        token = jose_jwt.encode(
            {
                "sub": "1",
                "role": "user",
                "exp": datetime.now(UTC) - timedelta(hours=1),
            },
            os.environ["JWT_SECRET_KEY"],
            algorithm=_ALGORITHM,
        )
        with pytest.raises(ExpiredSignatureError):
            decode_access_token(token)


# ── Secret key helper ─────────────────────────────────────────────────


class TestSecretKey:
    def test_get_secret_key_returns_value(self):
        key = _get_secret_key()
        assert isinstance(key, str)
        assert len(key) > 0

    def test_missing_secret_key_raises(self, monkeypatch):
        monkeypatch.delenv("JWT_SECRET_KEY", raising=False)
        with pytest.raises(RuntimeError, match="Missing JWT_SECRET_KEY"):
            _get_secret_key()
