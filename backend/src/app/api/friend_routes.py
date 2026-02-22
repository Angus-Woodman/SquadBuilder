"""Friend routes: send request, accept, list, remove, view friend squads."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr
from sqlalchemy import or_, select

from app.auth import get_current_user
from app.db.models import Friendship, FriendshipStatus, Squad, User
from app.db.session import get_sessionmaker

router = APIRouter(prefix="/friends", tags=["friends"])


# ── Schemas ───────────────────────────────────────────────────────────


class FriendRequestBody(BaseModel):
    email: EmailStr


class FriendResponse(BaseModel):
    friendship_id: int
    user_id: int
    display_name: str
    email: str
    status: str
    direction: str  # "sent" | "received"


class FriendSquadResponse(BaseModel):
    id: int
    name: str
    player_ids: list[int]
    created_at: str


def _friend_dict(f: Friendship, perspective_user_id: int) -> dict[str, Any]:
    """Return a dict describing the *other* person in the friendship."""
    if f.user_id == perspective_user_id:
        other = f.addressee
        direction = "sent"
    else:
        other = f.requester
        direction = "received"
    return {
        "friendship_id": f.id,
        "user_id": other.id,
        "display_name": other.display_name,
        "email": other.email,
        "status": f.status.value if isinstance(f.status, FriendshipStatus) else f.status,
        "direction": direction,
    }


# ── Endpoints ─────────────────────────────────────────────────────────


@router.get("/", response_model=list[FriendResponse])
def list_friends(user: User = Depends(get_current_user)):
    Session = get_sessionmaker()
    with Session() as db:
        friendships = db.scalars(
            select(Friendship)
            .where(or_(Friendship.user_id == user.id, Friendship.friend_id == user.id))
            .order_by(Friendship.created_at.desc())
        ).all()
        # Eagerly load related users
        result = []
        for f in friendships:
            # Manually load the other user if not loaded
            if f.user_id == user.id:
                other = db.get(User, f.friend_id)
            else:
                other = db.get(User, f.user_id)
            if other is None:
                continue
            direction = "sent" if f.user_id == user.id else "received"
            result.append(
                {
                    "friendship_id": f.id,
                    "user_id": other.id,
                    "display_name": other.display_name,
                    "email": other.email,
                    "status": f.status.value
                    if isinstance(f.status, FriendshipStatus)
                    else f.status,
                    "direction": direction,
                }
            )
        return result


@router.post("/request", response_model=FriendResponse, status_code=status.HTTP_201_CREATED)
def send_friend_request(req: FriendRequestBody, user: User = Depends(get_current_user)):
    Session = get_sessionmaker()
    with Session() as db:
        target = db.scalar(select(User).where(User.email == req.email.lower()))
        if target is None:
            raise HTTPException(status_code=404, detail="User not found")
        if target.id == user.id:
            raise HTTPException(status_code=400, detail="Cannot friend yourself")

        # Check existing friendship in either direction
        existing = db.scalar(
            select(Friendship).where(
                or_(
                    (Friendship.user_id == user.id) & (Friendship.friend_id == target.id),
                    (Friendship.user_id == target.id) & (Friendship.friend_id == user.id),
                )
            )
        )
        if existing:
            raise HTTPException(status_code=409, detail="Friendship already exists")

        friendship = Friendship(
            user_id=user.id,
            friend_id=target.id,
            status=FriendshipStatus.pending,
        )
        db.add(friendship)
        db.commit()
        db.refresh(friendship)

        return {
            "friendship_id": friendship.id,
            "user_id": target.id,
            "display_name": target.display_name,
            "email": target.email,
            "status": friendship.status.value,
            "direction": "sent",
        }


@router.put("/{friendship_id}/accept", response_model=FriendResponse)
def accept_friend_request(friendship_id: int, user: User = Depends(get_current_user)):
    Session = get_sessionmaker()
    with Session() as db:
        friendship = db.scalar(
            select(Friendship).where(
                Friendship.id == friendship_id,
                Friendship.friend_id == user.id,  # only the *addressee* can accept
                Friendship.status == FriendshipStatus.pending,
            )
        )
        if friendship is None:
            raise HTTPException(status_code=404, detail="Pending request not found")

        friendship.status = FriendshipStatus.accepted
        db.commit()
        db.refresh(friendship)

        requester = db.get(User, friendship.user_id)
        return {
            "friendship_id": friendship.id,
            "user_id": requester.id if requester else 0,
            "display_name": requester.display_name if requester else "",
            "email": requester.email if requester else "",
            "status": friendship.status.value,
            "direction": "received",
        }


@router.delete("/{friendship_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_friend(friendship_id: int, user: User = Depends(get_current_user)):
    Session = get_sessionmaker()
    with Session() as db:
        friendship = db.scalar(
            select(Friendship).where(
                Friendship.id == friendship_id,
                or_(Friendship.user_id == user.id, Friendship.friend_id == user.id),
            )
        )
        if friendship is None:
            raise HTTPException(status_code=404, detail="Friendship not found")
        db.delete(friendship)
        db.commit()


@router.get("/{friend_user_id}/squads", response_model=list[FriendSquadResponse])
def get_friend_squads(friend_user_id: int, user: User = Depends(get_current_user)):
    """View a friend's saved squads (only if friendship is accepted)."""
    Session = get_sessionmaker()
    with Session() as db:
        # Verify accepted friendship
        friendship = db.scalar(
            select(Friendship).where(
                Friendship.status == FriendshipStatus.accepted,
                or_(
                    (Friendship.user_id == user.id) & (Friendship.friend_id == friend_user_id),
                    (Friendship.user_id == friend_user_id) & (Friendship.friend_id == user.id),
                ),
            )
        )
        if friendship is None:
            raise HTTPException(status_code=403, detail="Not friends with this user")

        squads = db.scalars(
            select(Squad).where(Squad.user_id == friend_user_id).order_by(Squad.created_at.desc())
        ).all()
        return [
            {
                "id": s.id,
                "name": s.name,
                "player_ids": s.player_ids,
                "created_at": s.created_at.isoformat() if s.created_at else "",
            }
            for s in squads
        ]
