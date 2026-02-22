from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel


@asynccontextmanager
async def lifespan(_app: FastAPI):
    """Load backend/.env for local dev.
    In production you'd set env vars via your process manager/container."""
    backend_dir = Path(__file__).resolve().parents[3]  # .../backend
    load_dotenv(backend_dir / ".env")
    yield


app = FastAPI(title="Squad Builder API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class RefreshRequest(BaseModel):
    competition: list[str] = ["PL"]


def _player_to_dict(p: Any) -> dict[str, Any]:
    return {
        "player_id": p.player_id,
        "name": p.name,
        "position": p.position,
        "nationality": p.nationality,
        "date_of_birth": p.date_of_birth.isoformat() if p.date_of_birth else None,
    }


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/players")
def get_players(nationality: str | None = None, limit: int = 200) -> dict[str, Any]:
    if limit < 1 or limit > 2000:
        raise HTTPException(status_code=400, detail="limit must be between 1 and 2000")

    from app.db.queries import list_players

    players = list_players(nationality=nationality, limit=limit)
    players_dicts = [_player_to_dict(p) for p in players]

    return {"count": len(players_dicts), "players": players_dicts}


@app.post("/refresh")
def refresh(req: RefreshRequest) -> dict[str, Any]:
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
