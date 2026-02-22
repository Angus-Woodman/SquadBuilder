from sqlalchemy import func, select

from app.db.models import Player
from app.db.session import get_sessionmaker


def list_players(nationality: str | None = None, limit: int | None = None) -> list[Player]:

    SessionLocal = get_sessionmaker()

    stmt = select(Player).order_by(Player.name)
    if nationality:
        stmt = stmt.where(func.lower(Player.nationality) == nationality.lower())
    if limit:
        stmt = stmt.limit(limit)

    with SessionLocal() as db:
        return list(db.scalars(stmt).all())
