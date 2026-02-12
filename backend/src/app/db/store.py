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
            },
        )
    )

    with SessionLocal() as db:
        db.execute(stmt)
        db.commit()

    return len(rows)
