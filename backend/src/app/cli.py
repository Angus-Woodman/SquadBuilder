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

    photos_cmd = sub.add_parser("enrich-photos", help="Fetch player photos from TheSportsDB")
    photos_cmd.add_argument(
        "--nationality",
        "-n",
        default="England",
        help="Only enrich players of this nationality (default: England)",
    )
    photos_cmd.add_argument(
        "--delay",
        type=float,
        default=2.0,
        help="Seconds between API calls (default: 2.0)",
    )
    photos_cmd.add_argument(
        "--skip-existing",
        action="store_true",
        help="Skip players that already have a photo_url",
    )

    caps_cmd = sub.add_parser("enrich-caps", help="Fetch England caps/goals from eu-football.info")
    caps_cmd.add_argument(
        "--delay",
        type=float,
        default=1.0,
        help="Seconds between page requests (default: 1.0)",
    )
    caps_cmd.add_argument(
        "--max-pages",
        type=int,
        default=None,
        help="Stop after N pages (default: all ~31 pages)",
    )

    stats_cmd = sub.add_parser(
        "enrich-stats", help="Fetch current-season club stats from Understat"
    )
    stats_cmd.add_argument(
        "--nationality",
        "-n",
        default="England",
        help="Only enrich players of this nationality (default: England)",
    )
    stats_cmd.add_argument(
        "--delay",
        type=float,
        default=1.0,
        help="Seconds between league requests (default: 1.0)",
    )
    stats_cmd.add_argument(
        "--leagues",
        nargs="+",
        default=None,
        help="Leagues to query (default: all 5). Options: EPL La_liga Bundesliga Serie_A Ligue_1",
    )

    sportsdb_cmd = sub.add_parser(
        "enrich-sportsdb",
        help="Fetch preferred foot, photos, and club from TheSportsDB",
    )
    sportsdb_cmd.add_argument(
        "--nationality",
        "-n",
        default="England",
        help="Only enrich players of this nationality (default: England)",
    )
    sportsdb_cmd.add_argument(
        "--delay",
        type=float,
        default=4.0,
        help="Seconds between player lookups (default: 4.0, ~30 req/min free tier)",
    )
    sportsdb_cmd.add_argument(
        "--skip-existing",
        action="store_true",
        help="Skip players that already have a preferred_foot value",
    )

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

    elif args.command == "enrich-photos":
        from app.db.queries import list_players
        from app.db.store import update_player_photos
        from app.ingest.enrich import enrich_photos

        db_players = list_players(nationality=args.nationality)
        player_dicts = [
            {"player_id": p.player_id, "name": p.name, "photo_url": p.photo_url} for p in db_players
        ]

        if args.skip_existing:
            player_dicts = [p for p in player_dicts if not p.get("photo_url")]

        if not player_dicts:
            print("No players to enrich.")
            return

        print(f"Enriching photos for {len(player_dicts)} players...")

        batch_size = 15
        total_found = 0
        total_updated = 0

        for start in range(0, len(player_dicts), batch_size):
            batch = player_dicts[start : start + batch_size]
            batch_num = start // batch_size + 1
            total_batches = (len(player_dicts) + batch_size - 1) // batch_size

            def progress(i: int, total: int, name: str, _start: int = start) -> None:
                print(f"  [{_start + i}/{len(player_dicts)}] {name}")

            found = enrich_photos(batch, delay=args.delay, on_progress=progress)
            updated = update_player_photos(batch)
            total_found += found
            total_updated += updated
            print(f"  -- batch {batch_num}/{total_batches}: {found} photos found, {updated} saved")

        print(
            f"Done: {total_found} photos found, {total_updated} rows updated (of {len(player_dicts)} players)"
        )

    elif args.command == "enrich-caps":
        from app.db.queries import list_players
        from app.db.store import update_player_caps
        from app.ingest.caps import match_players, scrape_all_pages

        # 1. Scrape eu-football.info
        def progress(page: int, total: int, count: int) -> None:
            print(f"  Page {page}/{total} — {count} players scraped so far")

        print("Scraping England caps/goals from eu-football.info...")
        scraped = scrape_all_pages(
            delay=args.delay,
            max_pages=args.max_pages,
            on_progress=progress,
        )
        print(f"Scraped {len(scraped)} capped England players total.")

        # 2. Match against DB players
        db_players = list_players(nationality="England")
        db_dicts = [
            {
                "player_id": p.player_id,
                "name": p.name,
                "date_of_birth": p.date_of_birth,
            }
            for p in db_players
        ]
        matched = match_players(scraped, db_dicts)
        print(f"Matched {len(matched)} of {len(db_dicts)} DB players.")

        # 3. Update DB
        if matched:
            updated = update_player_caps(matched)
            print(f"Updated {updated} player rows with caps/goals data.")
        else:
            print("No matches found — nothing to update.")

    elif args.command == "enrich-stats":
        from app.db.queries import list_players
        from app.db.store import update_player_season_stats
        from app.ingest.season_stats import fetch_all_leagues, match_players

        # 1. Fetch stats from Understat
        def stats_progress(i: int, total: int, league: str, count: int) -> None:
            print(f"  [{i}/{total}] {league}: {count} players")

        print("Fetching current-season stats from Understat...")
        understat_players = fetch_all_leagues(
            leagues=args.leagues,
            delay=args.delay,
            on_progress=stats_progress,
        )
        print(f"Fetched {len(understat_players)} player-season entries across all leagues.")

        # 2. Match against DB players
        db_players = list_players(nationality=args.nationality)
        db_dicts = [
            {
                "player_id": p.player_id,
                "name": p.name,
                "club": p.club,
            }
            for p in db_players
        ]
        matched = match_players(understat_players, db_dicts)
        print(f"Matched {len(matched)} of {len(db_dicts)} DB players.")

        # 3. Update DB
        if matched:
            updated = update_player_season_stats(matched)
            print(f"Updated {updated} player rows with season stats.")
        else:
            print("No matches found — nothing to update.")

    elif args.command == "enrich-sportsdb":
        from app.db.queries import list_players
        from app.db.store import update_player_sportsdb
        from app.ingest.sportsdb import enrich_from_sportsdb

        db_players = list_players(nationality=args.nationality)
        player_dicts = [
            {
                "player_id": p.player_id,
                "name": p.name,
                "photo_url": p.photo_url,
                "club": p.club,
                "preferred_foot": p.preferred_foot,
            }
            for p in db_players
        ]

        if args.skip_existing:
            player_dicts = [p for p in player_dicts if not p.get("preferred_foot")]

        if not player_dicts:
            print("No players to enrich.")
            return

        print(f"Enriching {len(player_dicts)} players from TheSportsDB...")

        batch_size = 15
        total_found = 0
        total_updated = 0

        for start in range(0, len(player_dicts), batch_size):
            batch = player_dicts[start : start + batch_size]
            batch_num = start // batch_size + 1
            total_batches = (len(player_dicts) + batch_size - 1) // batch_size

            def progress(i: int, total: int, name: str, _start: int = start) -> None:
                print(f"  [{_start + i}/{len(player_dicts)}] {name}")

            found = enrich_from_sportsdb(batch, delay=args.delay, on_progress=progress)
            updated = update_player_sportsdb(batch)
            total_found += found
            total_updated += updated
            print(f"  -- batch {batch_num}/{total_batches}: {found} enriched, {updated} saved")

        print(
            f"Done: {total_found} players enriched, {total_updated} rows updated "
            f"(of {len(player_dicts)} players)"
        )


if __name__ == "__main__":
    main()
