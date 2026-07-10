from __future__ import annotations

import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from fastapi import APIRouter, Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from slowapi.errors import RateLimitExceeded
from sqlalchemy import select
from sqlalchemy.orm import Session
from starlette.requests import Request
from starlette.responses import JSONResponse

from app.auth import require_admin
from app.db.models import SuggestedPlayer
from app.db.session import get_db
from app.rate_limit import limiter


def _parse_csv(value: str | None) -> list[str]:
    if not value:
        return []
    return [item.strip() for item in value.split(",") if item.strip()]


def get_allowed_origins() -> list[str]:
    origins = os.getenv("ALLOWED_ORIGINS")
    if origins:
        return _parse_csv(origins)
    return ["http://localhost:5173", "http://127.0.0.1:5173"]


def should_create_tables() -> bool:
    value = os.getenv("AUTO_CREATE_TABLES", "1").strip().lower()
    return value not in ("0", "false", "no", "off", "")


@asynccontextmanager
async def lifespan(_app: FastAPI):
    """Load backend/.env for local dev.
    In production you'd set env vars via your process manager/container."""
    backend_dir = Path(__file__).resolve().parents[3]  # .../backend
    load_dotenv(backend_dir / ".env")

    if should_create_tables():
        from app.db.bootstrap import create_tables

        create_tables()

    yield


app = FastAPI(title="Squad Builder API", lifespan=lifespan)

# ── Rate limiting ─────────────────────────────────────────────────────

app.state.limiter = limiter


@app.exception_handler(RateLimitExceeded)
async def _rate_limit_handler(request: Request, exc: RateLimitExceeded):
    return JSONResponse(
        status_code=429,
        content={"detail": "Rate limit exceeded. Try again later."},
    )


app.add_middleware(
    CORSMiddleware,
    allow_origins=get_allowed_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── API router (all endpoints live under /api) ────────────────────────

from app.api.admin_routes import router as admin_router  # noqa: E402
from app.api.auth_routes import router as auth_router  # noqa: E402
from app.api.friend_routes import router as friends_router  # noqa: E402
from app.api.squad_routes import router as squads_router  # noqa: E402

api = APIRouter(prefix="/api")

api.include_router(auth_router)
api.include_router(squads_router)
api.include_router(friends_router)
api.include_router(admin_router)


# ── Inline endpoints ──────────────────────────────────────────────────


class RefreshRequest(BaseModel):
    competition: list[str] = ["PL"]


@api.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@api.get("/players")
def get_players(nationality: str | None = None, limit: int = 200) -> dict[str, Any]:
    if limit < 1 or limit > 2000:
        raise HTTPException(status_code=400, detail="limit must be between 1 and 2000")

    from app.db.queries import list_players

    players = list_players(nationality=nationality, limit=limit)
    return {"count": len(players), "players": [p.to_dict() for p in players]}


@api.get("/suggested")
def get_suggested_public(db: Session = Depends(get_db)) -> dict[str, Any]:
    """Public endpoint: returns the list of suggested player IDs."""
    rows = db.scalars(
        select(SuggestedPlayer.player_id).where(SuggestedPlayer.is_active.is_(True))
    ).all()
    return {"player_ids": list(rows)}


@api.post("/refresh")
def refresh(req: RefreshRequest, _admin=Depends(require_admin)) -> dict[str, Any]:
    """Re-fetch player data from the football-data API (admin only)."""
    try:
        from app.db.bootstrap import create_tables
        from app.db.store import upsert_players
        from app.ingest.fetch import fetch_teams_from_league
        from app.ingest.transform import transform_many_competitions

        create_tables()

        raw = {c: fetch_teams_from_league(c) for c in req.competition}
        transformed = transform_many_competitions(raw)

        players = transformed["players"]
        upsert_players(players)

        return {
            "competition": req.competition,
            "processed_players": len(players),
            "counts": transformed.get("counts"),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


app.include_router(api)
