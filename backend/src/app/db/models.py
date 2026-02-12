from datetime import date

from sqlalchemy import Date, Integer, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class Player(Base):
    __tablename__ = "players"

    player_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    position: Mapped[str | None] = mapped_column(String, nullable=True)
    nationality: Mapped[str | None] = mapped_column(String, nullable=True)
    date_of_birth: Mapped[date | None] = mapped_column(Date, nullable=True)
