import argparse
from pathlib import Path

from dotenv import load_dotenv


def main() -> None:
    # Loads backend/.env into environment variables for local runs
    backend_dir = Path(__file__).resolve().parents[2]  # .../backend
    load_dotenv(backend_dir / ".env")

    parser = argparse.ArgumentParser(prog="app")
    sub = parser.add_subparsers(dest="command", required=True)

    refresh = sub.add_parser("refresh", help="Fetch, transform, and upsert players into Postgres")
    refresh.add_argument(
        "--competition",
        "-c",
        nargs="+",
        required=True,
        help="Competition code(s) to fetch teams for. e.g. PL BL1 SA PD FL1",
    )

    list_cmd = sub.add_parser("list", help="List players from the database")
    list_cmd.add_argument("--nationality", "-n", default=None)

    args = parser.parse_args()

    if args.command == "refresh":
        from app.db.bootstrap import create_tables
        from app.db.store import upsert_players
        from app.ingest.fetch import fetch_teams_from_league
        from app.ingest.transform import transform_many_competitions

        create_tables()

        raw = {c: fetch_teams_from_league(c) for c in args.competition}
        transformed = transform_many_competitions(raw)

        inserted = upsert_players(transformed["players"])
        print(f"Upserted {inserted} player rows")

    elif args.command == "list":
        from app.db.queries import list_players

        players = list_players(args.nationality)
        for p in players[:50]:
            print(f"{p.player_id}: {p.name} ({p.position}) [{p.nationality}]")
        print(f"Total: {len(players)}")


if __name__ == "__main__":
    main()
