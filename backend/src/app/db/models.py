import enum
from datetime import date, datetime
from typing import Any

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    event,
    func,
)
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.schema import DDL


class Base(DeclarativeBase):
    pass


# ── Enums ─────────────────────────────────────────────────────────────


class UserRole(enum.StrEnum):
    user = "user"
    admin = "admin"


class FriendshipStatus(enum.StrEnum):
    pending = "pending"
    accepted = "accepted"


# ── Player (existing) ────────────────────────────────────────────────


class Player(Base):
    __tablename__ = "players"

    player_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    position: Mapped[str | None] = mapped_column(String, nullable=True)
    nationality: Mapped[str | None] = mapped_column(String, nullable=True)
    date_of_birth: Mapped[date | None] = mapped_column(Date, nullable=True)
    club: Mapped[str | None] = mapped_column(String, nullable=True)
    shirt_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    photo_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    england_caps: Mapped[int | None] = mapped_column(Integer, nullable=True)
    england_goals: Mapped[int | None] = mapped_column(Integer, nullable=True)
    preferred_foot: Mapped[str | None] = mapped_column(String, nullable=True)
    season_games: Mapped[int | None] = mapped_column(Integer, nullable=True)
    season_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    season_goals: Mapped[int | None] = mapped_column(Integer, nullable=True)
    season_assists: Mapped[int | None] = mapped_column(Integer, nullable=True)
    season_xg: Mapped[str | None] = mapped_column(String, nullable=True)
    season_xa: Mapped[str | None] = mapped_column(String, nullable=True)
    season_yellow_cards: Mapped[int | None] = mapped_column(Integer, nullable=True)
    season_red_cards: Mapped[int | None] = mapped_column(Integer, nullable=True)
    season_key_passes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    season_shots: Mapped[int | None] = mapped_column(Integer, nullable=True)

    def to_dict(self) -> dict[str, Any]:
        return {
            "player_id": self.player_id,
            "name": self.name,
            "position": self.position,
            "nationality": self.nationality,
            "date_of_birth": self.date_of_birth.isoformat() if self.date_of_birth else None,
            "club": self.club,
            "shirt_number": self.shirt_number,
            "photo_url": self.photo_url,
            "england_caps": self.england_caps,
            "england_goals": self.england_goals,
            "preferred_foot": self.preferred_foot,
            "season_games": self.season_games,
            "season_minutes": self.season_minutes,
            "season_goals": self.season_goals,
            "season_assists": self.season_assists,
            "season_xg": self.season_xg,
            "season_xa": self.season_xa,
            "season_yellow_cards": self.season_yellow_cards,
            "season_red_cards": self.season_red_cards,
            "season_key_passes": self.season_key_passes,
            "season_shots": self.season_shots,
        }


# ── User ──────────────────────────────────────────────────────────────


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String, unique=True, nullable=False, index=True)
    display_name: Mapped[str] = mapped_column(String, nullable=False)
    password_hash: Mapped[str] = mapped_column(Text, nullable=False)
    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole, name="user_role", native_enum=False),
        default=UserRole.user,
        server_default="user",
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    squads: Mapped[list["Squad"]] = relationship(
        back_populates="owner", cascade="all, delete-orphan"
    )

    # friendships where this user initiated
    sent_requests: Mapped[list["Friendship"]] = relationship(
        foreign_keys="Friendship.user_id", back_populates="requester", cascade="all, delete-orphan"
    )
    received_requests: Mapped[list["Friendship"]] = relationship(
        foreign_keys="Friendship.friend_id",
        back_populates="addressee",
        cascade="all, delete-orphan",
    )

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "email": self.email,
            "display_name": self.display_name,
            "role": self.role.value if isinstance(self.role, UserRole) else self.role,
            "created_at": self.created_at.isoformat() if self.created_at else "",
        }


# ── Squad ─────────────────────────────────────────────────────────────


class Squad(Base):
    __tablename__ = "squads"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String, nullable=False)
    # NOTE: a proper join table (squad_players) would enforce FK integrity on
    # player IDs and survive player deletions.  Left as ARRAY for now; migrate
    # when Alembic is set up.
    player_ids: Mapped[list[int]] = mapped_column(ARRAY(Integer), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    owner: Mapped["User"] = relationship(back_populates="squads")

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "player_ids": self.player_ids,
            "created_at": self.created_at.isoformat() if self.created_at else "",
        }


# ── Friendship ────────────────────────────────────────────────────────


class Friendship(Base):
    __tablename__ = "friendships"
    __table_args__ = (UniqueConstraint("user_id", "friend_id", name="uq_friendship_pair"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    friend_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    status: Mapped[FriendshipStatus] = mapped_column(
        Enum(FriendshipStatus, name="friendship_status", native_enum=False),
        default=FriendshipStatus.pending,
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    requester: Mapped["User"] = relationship(foreign_keys=[user_id], back_populates="sent_requests")
    addressee: Mapped["User"] = relationship(
        foreign_keys=[friend_id], back_populates="received_requests"
    )


# Prevent both (A→B) and (B→A) from existing — the app checks in Python,
# but this index is the DB-level safety net against race conditions.
event.listen(
    Friendship.__table__,
    "after_create",
    DDL(
        "CREATE UNIQUE INDEX IF NOT EXISTS uq_friendship_symmetric "
        "ON friendships (LEAST(user_id, friend_id), GREATEST(user_id, friend_id))"
    ),
)


# ── Suggested Players (admin-managed) ────────────────────────────────


class SuggestedPlayer(Base):
    __tablename__ = "suggested_players"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    player_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("players.player_id", ondelete="CASCADE"), unique=True, nullable=False
    )
    added_by: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, default=True, server_default="true", nullable=False
    )
