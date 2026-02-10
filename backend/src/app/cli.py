import json
from dotenv import load_dotenv

from ingest.fetch import fetch_pl_teams


def main() -> None:
    # Loads backend/.env into environment variables for local runs
    load_dotenv()

    data = fetch_pl_teams()
    teams = data.get("teams", [])
    for t in teams:
        print(f"{t.get('id')}: {t.get('name')}")



if __name__ == "__main__":
    main()
