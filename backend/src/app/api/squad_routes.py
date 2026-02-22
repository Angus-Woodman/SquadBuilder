"""Squad CRUD routes: list, create, delete saved squads."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import or_, select

from app.auth import get_current_user
from app.db.models import Player, Squad, User
from app.db.session import get_sessionmaker

router = APIRouter(prefix="/squads", tags=["squads"])


# ── Schemas ───────────────────────────────────────────────────────────


class CreateSquadRequest(BaseModel):
    name: str
    player_ids: list[int]


class SquadResponse(BaseModel):
    id: int
    name: str
    player_ids: list[int]
    created_at: str


def _squad_dict(s: Squad) -> dict[str, Any]:
    return {
        "id": s.id,
        "name": s.name,
        "player_ids": s.player_ids,
        "created_at": s.created_at.isoformat() if s.created_at else "",
    }


# ── Endpoints ─────────────────────────────────────────────────────────


@router.get("/", response_model=list[SquadResponse])
def list_squads(user: User = Depends(get_current_user)):
    Session = get_sessionmaker()
    with Session() as db:
        squads = db.scalars(
            select(Squad).where(Squad.user_id == user.id).order_by(Squad.created_at.desc())
        ).all()
        return [_squad_dict(s) for s in squads]


@router.get("/{squad_id}")
def get_squad(squad_id: int, user: User = Depends(get_current_user)) -> dict[str, Any]:
    """Return a single squad with full player details.

    Works for the user's own squads as well as squads belonging to an
    accepted friend.
    """
    Session = get_sessionmaker()
    with Session() as db:
        squad = db.scalar(select(Squad).where(Squad.id == squad_id))
        if squad is None:
            raise HTTPException(status_code=404, detail="Squad not found")

        # Authorisation: own squad or accepted friendship with the owner
        if squad.user_id != user.id:
            from app.db.models import Friendship, FriendshipStatus

            friendship = db.scalar(
                select(Friendship).where(
                    Friendship.status == FriendshipStatus.accepted,
                    or_(
                        (Friendship.user_id == user.id) & (Friendship.friend_id == squad.user_id),
                        (Friendship.user_id == squad.user_id) & (Friendship.friend_id == user.id),
                    ),
                )
            )
            if friendship is None:
                raise HTTPException(status_code=404, detail="Squad not found")

        owner = db.get(User, squad.user_id)

        # Fetch full player objects for the IDs in the squad
        players = db.scalars(select(Player).where(Player.player_id.in_(squad.player_ids))).all()
        player_list = [
            {
                "player_id": p.player_id,
                "name": p.name,
                "position": p.position,
                "nationality": p.nationality,
                "date_of_birth": p.date_of_birth.isoformat() if p.date_of_birth else None,
            }
            for p in players
        ]

        return {
            **_squad_dict(squad),
            "owner_id": squad.user_id,
            "owner_name": owner.display_name if owner else "Unknown",
            "players": player_list,
        }


@router.post("/", response_model=SquadResponse, status_code=status.HTTP_201_CREATED)
def create_squad(req: CreateSquadRequest, user: User = Depends(get_current_user)):
    if not req.name.strip():
        raise HTTPException(status_code=400, detail="Squad name is required")
    if not req.player_ids:
        raise HTTPException(status_code=400, detail="At least one player required")
    if len(req.player_ids) > 26:
        raise HTTPException(status_code=400, detail="Max 26 players allowed")

    Session = get_sessionmaker()
    with Session() as db:
        squad = Squad(
            user_id=user.id,
            name=req.name.strip(),
            player_ids=req.player_ids,
        )
        db.add(squad)
        db.commit()
        db.refresh(squad)
        return _squad_dict(squad)


@router.put("/{squad_id}", response_model=SquadResponse)
def update_squad(squad_id: int, req: CreateSquadRequest, user: User = Depends(get_current_user)):
    """Update an existing squad's name and player list."""
    if not req.name.strip():
        raise HTTPException(status_code=400, detail="Squad name is required")
    if not req.player_ids:
        raise HTTPException(status_code=400, detail="At least one player required")
    if len(req.player_ids) > 26:
        raise HTTPException(status_code=400, detail="Max 26 players allowed")

    Session = get_sessionmaker()
    with Session() as db:
        squad = db.scalar(select(Squad).where(Squad.id == squad_id, Squad.user_id == user.id))
        if squad is None:
            raise HTTPException(status_code=404, detail="Squad not found")
        squad.name = req.name.strip()
        squad.player_ids = req.player_ids
        db.commit()
        db.refresh(squad)
        return _squad_dict(squad)


@router.delete("/{squad_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_squad(squad_id: int, user: User = Depends(get_current_user)):
    Session = get_sessionmaker()
    with Session() as db:
        squad = db.scalar(select(Squad).where(Squad.id == squad_id, Squad.user_id == user.id))
        if squad is None:
            raise HTTPException(status_code=404, detail="Squad not found")
        db.delete(squad)
        db.commit()
