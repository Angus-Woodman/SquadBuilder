"""Squad CRUD routes: list, create, update, delete saved squads."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.db.models import Player, Squad, User
from app.db.session import get_db

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


# ── Helpers ───────────────────────────────────────────────────────────


def _validate_squad_payload(req: CreateSquadRequest) -> None:
    """Shared validation for create and update."""
    if not req.name.strip():
        raise HTTPException(status_code=400, detail="Squad name is required")
    if not req.player_ids:
        raise HTTPException(status_code=400, detail="At least one player required")
    if len(req.player_ids) > 26:
        raise HTTPException(status_code=400, detail="Max 26 players allowed")


# ── Endpoints ─────────────────────────────────────────────────────────


@router.get("/", response_model=list[SquadResponse])
def list_squads(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    squads = db.scalars(
        select(Squad).where(Squad.user_id == user.id).order_by(Squad.created_at.desc())
    ).all()
    return [s.to_dict() for s in squads]


@router.get("/{squad_id}")
def get_squad(
    squad_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Return a single squad with full player details.

    Works for the user's own squads as well as squads belonging to an
    accepted friend.
    """
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

    return {
        **squad.to_dict(),
        "owner_id": squad.user_id,
        "owner_name": owner.display_name if owner else "Unknown",
        "players": [p.to_dict() for p in players],
    }


@router.post("/", response_model=SquadResponse, status_code=status.HTTP_201_CREATED)
def create_squad(
    req: CreateSquadRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _validate_squad_payload(req)

    squad = Squad(
        user_id=user.id,
        name=req.name.strip(),
        player_ids=req.player_ids,
    )
    db.add(squad)
    db.commit()
    db.refresh(squad)
    return squad.to_dict()


@router.put("/{squad_id}", response_model=SquadResponse)
def update_squad(
    squad_id: int,
    req: CreateSquadRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update an existing squad's name and player list."""
    _validate_squad_payload(req)

    squad = db.scalar(select(Squad).where(Squad.id == squad_id, Squad.user_id == user.id))
    if squad is None:
        raise HTTPException(status_code=404, detail="Squad not found")
    squad.name = req.name.strip()
    squad.player_ids = req.player_ids
    db.commit()
    db.refresh(squad)
    return squad.to_dict()


@router.delete("/{squad_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_squad(
    squad_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    squad = db.scalar(select(Squad).where(Squad.id == squad_id, Squad.user_id == user.id))
    if squad is None:
        raise HTTPException(status_code=404, detail="Squad not found")
    db.delete(squad)
    db.commit()
