import argparse

from dotenv import load_dotenv

from app.ingest.fetch import fetch_teams_from_league


def main() -> None:
    # Loads backend/.env into environment variables for local runs
    load_dotenv()

    parser = argparse.ArgumentParser(prog="app")
    sub = parser.add_subparsers(dest="command", required=True)

    fetch = sub.add_parser("fetch", help="Fetch teams for a competition code (e.g. PL)")
    fetch.add_argument(
        "--competition",
        "-c",
        nargs="+",
        required=True,
        help="Competition code(s) to fetch teams for. e.g. PL BL1 SA PD FL1",
    )

    args = parser.parse_args()

    if args.command == "fetch":
        results = {}
        for comp in args.competition:
            results[comp] = fetch_teams_from_league(comp)

        # print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
