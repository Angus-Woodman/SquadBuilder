from collections.abc import Iterable
from typing import Any

from sqlalchemy.dialects.postgresql import insert

from app.db.models import Player
from app.db.session import get_sessionmaker


def upsert_players(players: Iterable[dict[str, Any]]) -> int:
    SessionLocal = get_sessionmaker()

    rows: list[dict[str, Any]] = []
    for p in players:
        rows.append(
            {
                "player_id": p["player_id"],
                "name": p.get("name") or "",
                "position": p.get("position"),
                "nationality": p.get("nationality"),
                "date_of_birth": p.get("date_of_birth"),
                "club": p.get("club"),
                "shirt_number": p.get("shirt_number"),
                "photo_url": p.get("photo_url"),
            }
        )

    if not rows:
        return 0

    stmt = (
        insert(Player)
        .values(rows)
        .on_conflict_do_update(
            index_elements=[Player.player_id],
            set_={
                "name": insert(Player).excluded.name,
                "position": insert(Player).excluded.position,
                "nationality": insert(Player).excluded.nationality,
                "date_of_birth": insert(Player).excluded.date_of_birth,
                "club": insert(Player).excluded.club,
                "shirt_number": insert(Player).excluded.shirt_number,
                "photo_url": insert(Player).excluded.photo_url,
            },
        )
    )

    with SessionLocal() as db:
        db.execute(stmt)
        db.commit()

    return len(rows)


def update_player_photos(players: Iterable[dict[str, Any]]) -> int:
    """Update only the photo_url column for players that have one."""
    SessionLocal = get_sessionmaker()
    updated = 0

    with SessionLocal() as db:
        for p in players:
            url = p.get("photo_url")
            if not url:
                continue
            result = db.execute(
                Player.__table__.update()
                .where(Player.player_id == p["player_id"])
                .values(photo_url=url)
            )
            updated += result.rowcount
        db.commit()

    return updated


def update_player_caps(players: Iterable[dict[str, Any]]) -> int:
    """Update england_caps and england_goals for matched players."""
    SessionLocal = get_sessionmaker()
    updated = 0

    with SessionLocal() as db:
        for p in players:
            caps = p.get("england_caps")
            goals = p.get("england_goals")
            if caps is None:
                continue
            result = db.execute(
                Player.__table__.update()
                .where(Player.player_id == p["player_id"])
                .values(england_caps=caps, england_goals=goals or 0)
            )
            updated += result.rowcount
        db.commit()

    return updated


def update_player_season_stats(players: Iterable[dict[str, Any]]) -> int:
    """Update season stats columns (and optionally club) for matched players."""
    SessionLocal = get_sessionmaker()
    updated = 0

    with SessionLocal() as db:
        for p in players:
            if p.get("season_minutes") is None:
                continue
            values: dict[str, Any] = {
                "season_games": p.get("season_games"),
                "season_minutes": p.get("season_minutes"),
                "season_goals": p.get("season_goals"),
                "season_assists": p.get("season_assists"),
                "season_xg": p.get("season_xg"),
                "season_xa": p.get("season_xa"),
                "season_yellow_cards": p.get("season_yellow_cards"),
                "season_red_cards": p.get("season_red_cards"),
                "season_key_passes": p.get("season_key_passes"),
                "season_shots": p.get("season_shots"),
            }
            # Backfill club from Understat if missing in DB
            if "club" in p:
                values["club"] = p["club"]

            result = db.execute(
                Player.__table__.update().where(Player.player_id == p["player_id"]).values(**values)
            )
            updated += result.rowcount
        db.commit()

    return updated


def update_player_sportsdb(players: Iterable[dict[str, Any]]) -> int:
    """Update preferred_foot, photo_url, and club from TheSportsDB data."""
    SessionLocal = get_sessionmaker()
    updated = 0

    with SessionLocal() as db:
        for p in players:
            values: dict[str, Any] = {}

            if p.get("preferred_foot"):
                values["preferred_foot"] = p["preferred_foot"]
            if p.get("photo_url"):
                values["photo_url"] = p["photo_url"]
            if p.get("club"):
                values["club"] = p["club"]

            if not values:
                continue

            result = db.execute(
                Player.__table__.update().where(Player.player_id == p["player_id"]).values(**values)
            )
            updated += result.rowcount
        db.commit()

    return updated
