from sqlalchemy import select

from app.db.models import Player
from app.db.session import get_sessionmaker

SessionLocal = get_sessionmaker()


def list_players(nationality: str | None = None) -> list[Player]:
    stmt = select(Player)
    if nationality:
        stmt = stmt.where(Player.nationality == nationality)

    with SessionLocal() as db:
        return list(db.scalars(stmt).all())
