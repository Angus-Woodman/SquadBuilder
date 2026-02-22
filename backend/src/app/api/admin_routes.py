"""Admin routes: manage suggested player list and data refresh."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr
from sqlalchemy import delete, select

from app.auth import hash_password, require_admin
from app.db.models import Player, SuggestedPlayer, User
from app.db.session import get_sessionmaker

router = APIRouter(prefix="/admin", tags=["admin"])


# ── Schemas ───────────────────────────────────────────────────────────


class SetSuggestedRequest(BaseModel):
    player_ids: list[int]


class SuggestedPlayerResponse(BaseModel):
    player_id: int
    name: str
    position: str | None
    nationality: str | None


class CreateUserRequest(BaseModel):
    email: EmailStr
    display_name: str
    password: str
    role: str = "user"


class UpdatePlayerRequest(BaseModel):
    name: str | None = None
    position: str | None = None
    nationality: str | None = None
    date_of_birth: str | None = None  # ISO date string


# ── Endpoints ─────────────────────────────────────────────────────────


@router.get("/suggested", response_model=list[SuggestedPlayerResponse])
def get_suggested(user: User = Depends(require_admin)):
    Session = get_sessionmaker()
    with Session() as db:
        rows = db.execute(
            select(SuggestedPlayer.player_id, Player.name, Player.position, Player.nationality)
            .join(Player, SuggestedPlayer.player_id == Player.player_id)
            .where(SuggestedPlayer.is_active.is_(True))
            .order_by(Player.name)
        ).all()
        return [
            {
                "player_id": r.player_id,
                "name": r.name,
                "position": r.position,
                "nationality": r.nationality,
            }
            for r in rows
        ]


@router.put("/suggested")
def set_suggested(req: SetSuggestedRequest, user: User = Depends(require_admin)) -> dict[str, Any]:
    """Replace the entire suggested list with the given player IDs."""
    Session = get_sessionmaker()
    with Session() as db:
        # Clear existing
        db.execute(delete(SuggestedPlayer))

        # Insert new
        for pid in req.player_ids:
            db.add(SuggestedPlayer(player_id=pid, added_by=user.id))

        db.commit()

    return {"count": len(req.player_ids)}


@router.get("/users")
def list_users(user: User = Depends(require_admin)) -> list[dict[str, Any]]:
    """List all users (admin only)."""
    Session = get_sessionmaker()
    with Session() as db:
        users = db.scalars(select(User).order_by(User.created_at.desc())).all()
        return [
            {
                "id": u.id,
                "email": u.email,
                "display_name": u.display_name,
                "role": u.role.value if hasattr(u.role, "value") else u.role,
                "created_at": u.created_at.isoformat() if u.created_at else "",
            }
            for u in users
        ]


@router.put("/users/{user_id}/role")
def set_user_role(user_id: int, role: str, user: User = Depends(require_admin)) -> dict[str, str]:
    """Promote/demote a user (admin only)."""
    from app.db.models import UserRole

    if role not in ("user", "admin"):
        raise HTTPException(status_code=400, detail="Role must be 'user' or 'admin'")

    Session = get_sessionmaker()
    with Session() as db:
        target = db.get(User, user_id)
        if target is None:
            raise HTTPException(status_code=404, detail="User not found")
        target.role = UserRole(role)
        db.commit()

    return {"status": "ok", "role": role}


# ── User CRUD ─────────────────────────────────────────────────────────


@router.post("/users")
def create_user(req: CreateUserRequest, user: User = Depends(require_admin)) -> dict[str, Any]:
    """Create a new user (admin only)."""
    from app.db.models import UserRole

    if req.role not in ("user", "admin"):
        raise HTTPException(status_code=400, detail="Role must be 'user' or 'admin'")

    Session = get_sessionmaker()
    with Session() as db:
        existing = db.scalars(select(User).where(User.email == req.email)).first()
        if existing:
            raise HTTPException(status_code=409, detail="A user with that email already exists")

        new_user = User(
            email=req.email,
            display_name=req.display_name,
            password_hash=hash_password(req.password),
            role=UserRole(req.role),
        )
        db.add(new_user)
        db.commit()
        db.refresh(new_user)

        return {
            "id": new_user.id,
            "email": new_user.email,
            "display_name": new_user.display_name,
            "role": new_user.role.value,
        }


@router.delete("/users/{user_id}")
def delete_user(user_id: int, user: User = Depends(require_admin)) -> dict[str, str]:
    """Delete a user account (admin only). Cannot delete yourself."""
    if user_id == user.id:
        raise HTTPException(status_code=400, detail="Cannot delete your own account")

    Session = get_sessionmaker()
    with Session() as db:
        target = db.get(User, user_id)
        if target is None:
            raise HTTPException(status_code=404, detail="User not found")
        db.delete(target)
        db.commit()

    return {"status": "ok"}


# ── Player search & edit ──────────────────────────────────────────────


@router.get("/players/search")
def search_players(q: str = "", user: User = Depends(require_admin)) -> list[dict[str, Any]]:
    """Search players by name (admin only). Returns up to 50 results."""
    Session = get_sessionmaker()
    with Session() as db:
        stmt = select(Player).where(Player.name.ilike(f"%{q}%")).order_by(Player.name).limit(50)
        players = db.scalars(stmt).all()
        return [
            {
                "player_id": p.player_id,
                "name": p.name,
                "position": p.position,
                "nationality": p.nationality,
                "date_of_birth": str(p.date_of_birth) if p.date_of_birth else None,
            }
            for p in players
        ]


@router.put("/players/{player_id}")
def update_player(
    player_id: int,
    req: UpdatePlayerRequest,
    user: User = Depends(require_admin),
) -> dict[str, Any]:
    """Update a player's data (admin only)."""
    from datetime import date as date_type

    Session = get_sessionmaker()
    with Session() as db:
        player = db.scalars(select(Player).where(Player.player_id == player_id)).first()
        if player is None:
            raise HTTPException(status_code=404, detail="Player not found")

        if req.name is not None:
            player.name = req.name
        if req.position is not None:
            player.position = req.position
        if req.nationality is not None:
            player.nationality = req.nationality
        if req.date_of_birth is not None:
            try:
                player.date_of_birth = date_type.fromisoformat(req.date_of_birth)
            except ValueError as err:
                raise HTTPException(
                    status_code=400, detail="Invalid date format, use YYYY-MM-DD"
                ) from err

        db.commit()
        db.refresh(player)

        return {
            "player_id": player.player_id,
            "name": player.name,
            "position": player.position,
            "nationality": player.nationality,
            "date_of_birth": str(player.date_of_birth) if player.date_of_birth else None,
        }
