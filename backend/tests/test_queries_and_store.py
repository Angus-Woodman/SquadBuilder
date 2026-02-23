"""Integration tests for the database layer: queries.py and store.py.

These tests exercise ``list_players`` and ``upsert_players`` against the
real PostgreSQL test database.
"""

from __future__ import annotations

from datetime import date

from conftest import create_player_in_db

# ── list_players (queries.py) ─────────────────────────────────────────


class TestListPlayers:
    def test_list_players_empty(self):
        from app.db.queries import list_players

        result = list_players()
        assert result == []

    def test_list_players_returns_all(self, db):
        create_player_in_db(db, player_id=1, name="Alpha")
        create_player_in_db(db, player_id=2, name="Beta")
        create_player_in_db(db, player_id=3, name="Gamma")

        from app.db.queries import list_players

        result = list_players()
        assert len(result) == 3

    def test_list_players_ordered_by_name(self, db):
        create_player_in_db(db, player_id=1, name="Zara")
        create_player_in_db(db, player_id=2, name="Alice")
        create_player_in_db(db, player_id=3, name="Mike")

        from app.db.queries import list_players

        result = list_players()
        names = [p.name for p in result]
        assert names == ["Alice", "Mike", "Zara"]

    def test_list_players_filter_nationality(self, db):
        create_player_in_db(db, player_id=1, name="Eng 1", nationality="England")
        create_player_in_db(db, player_id=2, name="Eng 2", nationality="England")
        create_player_in_db(db, player_id=3, name="Fra 1", nationality="France")

        from app.db.queries import list_players

        result = list_players(nationality="England")
        assert len(result) == 2
        assert all(p.nationality == "England" for p in result)

    def test_list_players_nationality_case_insensitive(self, db):
        create_player_in_db(db, player_id=1, name="Eng", nationality="England")

        from app.db.queries import list_players

        result = list_players(nationality="england")
        assert len(result) == 1

    def test_list_players_with_limit(self, db):
        for i in range(1, 11):
            create_player_in_db(db, player_id=i, name=f"Player {i:02d}")

        from app.db.queries import list_players

        result = list_players(limit=5)
        assert len(result) == 5

    def test_list_players_nationality_and_limit(self, db):
        for i in range(1, 6):
            create_player_in_db(db, player_id=i, name=f"Eng {i}", nationality="England")
        for i in range(6, 10):
            create_player_in_db(db, player_id=i, name=f"Fra {i}", nationality="France")

        from app.db.queries import list_players

        result = list_players(nationality="England", limit=3)
        assert len(result) == 3
        assert all(p.nationality == "England" for p in result)


# ── upsert_players (store.py) ────────────────────────────────────────


class TestUpsertPlayers:
    def test_upsert_insert_new(self, db):
        from app.db.store import upsert_players

        count = upsert_players(
            [
                {
                    "player_id": 100,
                    "name": "New Player",
                    "position": "Forward",
                    "nationality": "England",
                    "date_of_birth": date(2000, 1, 1),
                },
            ]
        )
        assert count == 1

        # Verify via query
        from app.db.queries import list_players

        players = list_players()
        assert len(players) == 1
        assert players[0].name == "New Player"

    def test_upsert_update_on_conflict(self, db):
        from app.db.store import upsert_players

        upsert_players(
            [
                {
                    "player_id": 200,
                    "name": "Original",
                    "position": "Forward",
                    "nationality": "England",
                    "date_of_birth": None,
                },
            ]
        )

        # Upsert same player_id with new data
        upsert_players(
            [
                {
                    "player_id": 200,
                    "name": "Updated",
                    "position": "Midfielder",
                    "nationality": "England",
                    "date_of_birth": date(1999, 6, 15),
                },
            ]
        )

        from app.db.queries import list_players

        players = list_players()
        assert len(players) == 1
        assert players[0].name == "Updated"
        assert players[0].position == "Midfielder"
        assert players[0].date_of_birth == date(1999, 6, 15)

    def test_upsert_empty_list(self):
        from app.db.store import upsert_players

        count = upsert_players([])
        assert count == 0

    def test_upsert_multiple_players(self, db):
        from app.db.store import upsert_players

        players = [
            {
                "player_id": i,
                "name": f"Player {i}",
                "position": "Forward",
                "nationality": "England",
                "date_of_birth": None,
            }
            for i in range(1, 6)
        ]

        count = upsert_players(players)
        assert count == 5

        from app.db.queries import list_players

        assert len(list_players()) == 5

    def test_upsert_handles_missing_optional_fields(self, db):
        from app.db.store import upsert_players

        count = upsert_players(
            [
                {
                    "player_id": 300,
                    "name": "Minimal",
                    # no position, nationality, or date_of_birth keys
                },
            ]
        )
        assert count == 1

        from app.db.queries import list_players

        p = list_players()[0]
        assert p.name == "Minimal"
        assert p.position is None
        assert p.nationality is None
        assert p.date_of_birth is None

    def test_upsert_mix_insert_and_update(self, db):
        from app.db.store import upsert_players

        # Insert first batch
        upsert_players(
            [
                {"player_id": 1, "name": "First", "nationality": "England"},
                {"player_id": 2, "name": "Second", "nationality": "France"},
            ]
        )

        # Second batch: update player 1, insert player 3
        count = upsert_players(
            [
                {"player_id": 1, "name": "First Updated", "nationality": "England"},
                {"player_id": 3, "name": "Third", "nationality": "Spain"},
            ]
        )
        assert count == 2

        from app.db.queries import list_players

        players = {p.player_id: p for p in list_players()}
        assert len(players) == 3
        assert players[1].name == "First Updated"
        assert players[3].name == "Third"
