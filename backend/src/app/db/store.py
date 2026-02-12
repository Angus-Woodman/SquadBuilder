from collections.abc import Iterable
from typing import Any

from sqlalchemy.dialects.postgresql import insert

from app.db.models import Player
from app.db.session import get_sessionmaker

SessionLocal = get_sessionmaker()


def upsert_players(players: Iterable[dict[str, Any]]) -> int:
    rows = []
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

    stmt = insert(Player).values(rows)
    stmt = stmt.on_conflict_do_update(
        index_elements=[Player.player_id],
        set_={
            "name": stmt.excluded.name,
            "position": stmt.excluded.position,
            "nationality": stmt.excluded.nationality,
            "date_of_birth": stmt.excluded.date_of_birth,
        },
    )

    with SessionLocal() as db:
        db.execute(stmt)
        db.commit()

    return len(rows)
