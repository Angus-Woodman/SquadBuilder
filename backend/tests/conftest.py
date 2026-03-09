"""Shared test fixtures for the squad-builder backend test suite.

Provides:
- A disposable ``squad_builder_test`` PostgreSQL database (same Docker instance)
- Automatic table creation / teardown per session
- Table truncation between every test for isolation
- FastAPI ``TestClient`` with auth helpers
- Convenience factories for users, players, squads, and friendships
"""

from __future__ import annotations

import os
from datetime import date
from typing import Any

import pytest
from sqlalchemy import create_engine, text

# ---------------------------------------------------------------------------
# Test database URL (same PG instance as dev, separate database)
# ---------------------------------------------------------------------------
_TEST_DB_URL = "postgresql+psycopg://squad:squad@localhost:5432/squad_builder_test"

# Tables to truncate, ordered so FK constraints aren't violated
_TABLES = ["suggested_players", "friendships", "squads", "users", "players"]


# ---------------------------------------------------------------------------
# Session-scoped: create the test database & tables once
# ---------------------------------------------------------------------------
@pytest.fixture(scope="session", autouse=True)
def _setup_test_database():
    """Create the ``squad_builder_test`` database and all tables."""
    # ── Ensure the test database exists ────────────────────────────────
    base_url = "postgresql+psycopg://squad:squad@localhost:5432/postgres"
    try:
        base_engine = create_engine(base_url, isolation_level="AUTOCOMMIT")
        with base_engine.connect() as conn:
            exists = conn.execute(
                text("SELECT 1 FROM pg_database WHERE datname = 'squad_builder_test'")
            ).fetchone()
            if not exists:
                conn.execute(text("CREATE DATABASE squad_builder_test"))
        base_engine.dispose()
    except Exception:
        pytest.skip("PostgreSQL is not available — skipping integration tests")

    # ── Point the application at the test database ─────────────────────
    os.environ["DATABASE_URL"] = _TEST_DB_URL
    os.environ["JWT_SECRET_KEY"] = "test-secret-key-for-testing-only"
    os.environ.setdefault("FOOTBALL_DATA_API_TOKEN", "test-token")

    # Clear lru_cache so the app picks up our test URL
    from app.db.session import get_engine, get_sessionmaker

    get_engine.cache_clear()
    get_sessionmaker.cache_clear()

    from app.db.models import Base

    engine = get_engine()
    Base.metadata.create_all(bind=engine)

    yield

    # ── Teardown ───────────────────────────────────────────────────────
    Base.metadata.drop_all(bind=engine)
    engine.dispose()
    get_engine.cache_clear()
    get_sessionmaker.cache_clear()


# ---------------------------------------------------------------------------
# Function-scoped: clean slate for every test
# ---------------------------------------------------------------------------
@pytest.fixture(autouse=True)
def _clean_tables():
    """Truncate all tables before each test so tests start with a clean DB."""
    from app.db.session import get_sessionmaker

    Session = get_sessionmaker()
    with Session() as db:
        for table in _TABLES:
            db.execute(text(f"TRUNCATE TABLE {table} CASCADE"))
        db.commit()
    yield


# ---------------------------------------------------------------------------
# FastAPI test client
# ---------------------------------------------------------------------------
@pytest.fixture()
def client():
    """A ``starlette.testclient.TestClient`` bound to the FastAPI app."""
    from fastapi.testclient import TestClient

    from app.api.main import app
    from app.rate_limit import limiter

    # Disable rate limiting during tests so registration-heavy suites
    # don't hit the 10/minute cap.
    limiter.enabled = False

    with TestClient(app) as c:
        yield c

    limiter.enabled = True


# ---------------------------------------------------------------------------
# Direct DB session for test setup / assertions
# ---------------------------------------------------------------------------
@pytest.fixture()
def db():
    """A raw SQLAlchemy session for direct DB manipulation in tests."""
    from app.db.session import get_sessionmaker

    Session = get_sessionmaker()
    with Session() as session:
        yield session


# ---------------------------------------------------------------------------
# Helper factories
# ---------------------------------------------------------------------------
def register_user(
    client,
    *,
    email: str = "test@example.com",
    display_name: str = "Test User",
    password: str = "password123",
) -> dict[str, Any]:
    """Register a user via the API and return the full response JSON."""
    resp = client.post(
        "/api/auth/register",
        json={"email": email, "display_name": display_name, "password": password},
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


def auth_header(token: str) -> dict[str, str]:
    """Build an ``Authorization: Bearer …`` header dict."""
    return {"Authorization": f"Bearer {token}"}


def create_player_in_db(
    db,
    *,
    player_id: int = 1,
    name: str = "Test Player",
    position: str | None = "Forward",
    nationality: str | None = "England",
    date_of_birth: date | None = None,
    club: str | None = None,
    shirt_number: int | None = None,
    photo_url: str | None = None,
) -> None:
    """Insert a player row directly into the database."""
    from app.db.models import Player

    db.add(
        Player(
            player_id=player_id,
            name=name,
            position=position,
            nationality=nationality,
            date_of_birth=date_of_birth,
            club=club,
            shirt_number=shirt_number,
            photo_url=photo_url,
        )
    )
    db.commit()


def make_admin(db, user_id: int) -> None:
    """Promote a user to admin directly in the database."""
    from app.db.models import User, UserRole

    user = db.get(User, user_id)
    assert user is not None, f"User {user_id} not found"
    user.role = UserRole.admin
    db.commit()
