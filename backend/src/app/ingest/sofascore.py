"""Fetch player data from SofaScore.com.

Currently supports fetching squad data for a specific team via browser automation.

SofaScore provides:
- Player names
- Current positions
- Shirt numbers

Note: SofaScore heavily relies on JavaScript rendering and has anti-bot protections.
Browser automation (Playwright, Selenium) is required to fetch data.
"""

from __future__ import annotations

import json
import re
import time
from typing import Any

from bs4 import BeautifulSoup

# SofaScore team URL pattern (correct format: /football/team/{slug}/{id})
SOFASCORE_BASE = "https://www.sofascore.com/football/team"

# Common team IDs for reference
COMMON_TEAMS = {
    "chelsea": 38,
    "manchester-city": 17,
    "manchester-united": 33,
    "liverpool": 39,
    "arsenal": 42,
}

# Headers to mimic a real browser request
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
    "Accept-Encoding": "gzip, deflate",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
    "Cache-Control": "max-age=0",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
}


# ── Helper Functions ──────────────────────────────────────────────────


def _parse_sofascore_api_response(data: dict[str, Any]) -> list[dict[str, Any]]:
    """Parse player data from SofaScore API response."""
    players = []

    # Try different possible response structures
    players_list = data.get("players") or data.get("data") or data.get("squad") or []

    if not isinstance(players_list, list):
        return []

    for player_obj in players_list:
        if not isinstance(player_obj, dict):
            continue

        player_data: dict[str, Any] = {}

        # Extract name
        name = player_obj.get("name") or player_obj.get("player", {}).get("name")
        if name:
            player_data["name"] = name

        # Extract position
        position = player_obj.get("position") or player_obj.get("player", {}).get("position")
        if position:
            player_data["position"] = position

        # Extract shirt number
        shirt_number = player_obj.get("shirtNumber") or player_obj.get("shirt_number")
        if shirt_number is not None:
            try:
                player_data["shirt_number"] = int(shirt_number)
            except (ValueError, TypeError):
                pass

        if player_data.get("name"):
            players.append(player_data)

    return players


def _parse_next_data_players(content: str) -> list[dict[str, Any]]:
    """Extract player data from SofaScore's __NEXT_DATA__ JSON embedded in HTML.

    Parameters
    ----------
    content : str
        The HTML page content containing __NEXT_DATA__ script.

    Returns
    -------
    list[dict[str, Any]]
        List of player dicts with: name, position (if available), shirt_number (if available).
    """
    players = []

    # Extract __NEXT_DATA__ JSON from HTML
    match = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', content, re.DOTALL)
    if not match:
        return []

    try:
        data = json.loads(match.group(1))
    except json.JSONDecodeError as e:
        print(f"Warning: Could not parse __NEXT_DATA__ JSON: {e}")
        return []

    # Navigate to player data
    page_props = data.get("props", {}).get("pageProps", {})
    players_data = page_props.get("players", {})

    # Try different player lists (prefer 'players' as it's the main squad)
    player_lists = [
        players_data.get("players", []),  # Main squad
        players_data.get("foreignPlayers", []),  # Foreign players
        players_data.get("nationalPlayers", []),  # National players
    ]

    for player_list in player_lists:
        if not isinstance(player_list, list):
            continue

        for item in player_list:
            if not isinstance(item, dict):
                continue

            # Player data is nested under 'player' key
            player_obj = item.get("player", {})
            if not isinstance(player_obj, dict):
                continue

            player_data: dict[str, Any] = {}

            # Extract name
            name = player_obj.get("name")
            if name:
                player_data["name"] = name
            else:
                # Try firstName + lastName if name is not available
                first_name = player_obj.get("firstName", "").strip()
                last_name = player_obj.get("lastName", "").strip()
                if first_name or last_name:
                    player_data["name"] = f"{first_name} {last_name}".strip()

            # Extract position (might be in role or position field)
            position = (
                item.get("position")
                or player_obj.get("position")
                or item.get("role")
                or player_obj.get("role")
            )
            if position:
                player_data["position"] = position

            # Extract shirt number
            shirt_number = item.get("shirtNumber") or player_obj.get("shirtNumber")
            if shirt_number is not None:
                try:
                    player_data["shirt_number"] = int(shirt_number)
                except (ValueError, TypeError):
                    pass

            if player_data.get("name"):
                # Avoid duplicates
                if not any(p.get("name") == player_data.get("name") for p in players):
                    players.append(player_data)

    return players


def _parse_squad_from_html(soup: BeautifulSoup) -> list[dict[str, Any]]:
    """Extract player data from the SofaScore squad page HTML."""
    players = []

    # SofaScore uses various class names for squad data
    # Look for common player row patterns
    for elem in soup.find_all(re.compile(r"div|tr|li"), recursive=True):
        # Check if this element looks like a player row
        text = elem.get_text(strip=True)
        attrs_str = str(elem.attrs).lower()

        # Skip empty or very short elements
        if not text or len(text) < 3:
            continue

        # Look for player position indicators
        has_position = any(
            pos in text.upper()
            for pos in [
                "GK",
                "DEF",
                "MID",
                "FWD",
                "MIDFIELDER",
                "DEFENDER",
                "FORWARD",
                "GOALKEEPER",
            ]
        )

        # Look for shirt number patterns (usually 1-99)
        has_number = bool(re.search(r"#?\s*\d{1,2}\s", text)) or "player" in attrs_str

        # If it looks like it might be a player, try to extract data
        if has_position or has_number or "player" in attrs_str:
            player_data = _extract_player_from_row(elem)
            if player_data and player_data.get("name"):
                # Avoid duplicates
                if not any(p.get("name") == player_data.get("name") for p in players):
                    players.append(player_data)

    return players


def _extract_player_from_row(row) -> dict[str, Any] | None:
    """Extract a single player's data from a table row or div element."""
    player_data: dict[str, Any] = {}
    text = row.get_text(separator=" ", strip=True)

    if not text or len(text) < 2:
        return None

    # Split text into parts for analysis
    parts = text.split()

    # Try to extract name (usually the first 1-3 parts)
    # Look for capitalized words
    name_parts = []
    for _i, part in enumerate(parts[:5]):
        # Stop at position keywords or numbers
        if any(
            pos in part.upper() for pos in ["GK", "DEF", "MID", "FWD", "GOALKEEPER", "DEFENDER"]
        ):
            break
        if part.isdigit() and int(part) <= 99:
            break
        if len(part) > 1 and part[0].isupper():
            name_parts.append(part)

    if name_parts:
        player_data["name"] = " ".join(name_parts)
    else:
        return None

    # Try to extract position
    for part in parts:
        if part.upper() in [
            "GK",
            "DEF",
            "MID",
            "FWD",
            "CB",
            "RB",
            "LB",
            "CM",
            "CAM",
            "CDM",
            "LW",
            "RW",
            "ST",
        ]:
            player_data["position"] = part.upper()
            break
        if any(pos in part.upper() for pos in ["GOALKEEPER", "DEFENDER", "MIDFIELDER", "FORWARD"]):
            player_data["position"] = part
            break

    # Try to extract shirt number
    for _i, part in enumerate(parts):
        if part.isdigit():
            num = int(part)
            if 0 < num <= 99:
                player_data["shirt_number"] = num
                break
        # Look for # pattern
        if part.startswith("#") and part[1:].isdigit():
            player_data["shirt_number"] = int(part[1:])
            break

    return player_data if player_data.get("name") else None


# ── Public API Functions ───────────────────────────────────────────────


def fetch_sofascore_squad(team_slug: str, *, delay: float = 1.0) -> list[dict[str, Any]]:
    """Fetch squad data from SofaScore for a given team (HTTP only - shows info).

    This function demonstrates why browser automation is needed.
    Direct HTTP requests to SofaScore are blocked (403 Forbidden).

    Parameters
    ----------
    team_slug : str
        The URL slug for the team (e.g., "chelsea").
    delay : float
        Seconds to wait between requests to avoid rate-limiting.

    Returns
    -------
    list[dict[str, Any]]
        Empty list (HTTP requests are blocked).
    """
    print("=" * 70)
    print("⚠️  SofaScore Squad Scraper - Browser Automation Required")
    print("=" * 70)
    print()
    print("Direct HTTP requests to SofaScore are blocked (403 Forbidden).")
    print("This is because SofaScore heavily relies on JavaScript to render content.")
    print()
    print("To scrape SofaScore squad data, use one of these options:")
    print()
    print("OPTION 1: Use Playwright (Recommended)")
    print("-" * 70)
    print("  1. Install Playwright: pip install playwright")
    print("  2. Install browser: playwright install chromium")
    print("  3. Run the command:")
    print("     python -m app.cli sofascore-squad --team chelsea --use-playwright")
    print()
    print("OPTION 2: Use Selenium")
    print("-" * 70)
    print("  1. Install Selenium: pip install selenium")
    print("  2. Download ChromeDriver: https://chromedriver.chromium.org/")
    print("  3. Run the command:")
    print("     python -m app.cli sofascore-squad --team chelsea --use-selenium \\")
    print("       --chromedriver /path/to/chromedriver")
    print()
    print("=" * 70)

    return []


def fetch_sofascore_squad_with_playwright(
    team_slug: str,
    team_id: int | None = None,
    *,
    delay: float = 2.0,
    headless: bool = True,
) -> list[dict[str, Any]]:
    """Fetch squad data using Playwright browser automation.

    This is the recommended approach since SofaScore requires JavaScript rendering
    and blocks direct API calls.

    Parameters
    ----------
    team_slug : str
        The URL slug for the team (e.g., "chelsea").
    team_id : int, optional
        The SofaScore team ID (e.g., 38 for Chelsea).
        If not provided, will look up in COMMON_TEAMS.
    delay : float
        Seconds to wait after page load before extracting data.
    headless : bool
        If True, run browser in headless mode (no UI window).

    Returns
    -------
    list[dict[str, Any]]
        List of player dicts with: name, position, shirt_number.

    Requirements
    -----
    1. Install Playwright: pip install playwright
    2. Install browser: playwright install chromium
    """
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("Playwright is not installed. Install it with:")
        print("  pip install playwright")
        print("Then install the browser:")
        print("  playwright install chromium")
        return []

    # Look up team ID if not provided
    if not team_id and team_slug.lower() in COMMON_TEAMS:
        team_id = COMMON_TEAMS[team_slug.lower()]

    if not team_id:
        print(f"Error: Team ID required for '{team_slug}'")
        print(f"Known teams: {', '.join(COMMON_TEAMS.keys())}")
        return []

    players = []

    # Construct URL - correct format for SofaScore
    url = f"{SOFASCORE_BASE}/{team_slug}/{team_id}#tab:players"

    print(f"Launching browser to fetch: {url}")

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=headless)
            context = browser.new_context()
            page = context.new_page()

            # Set user agent
            page.set_extra_http_headers(HEADERS)

            # Navigate to page (without the #tab:players anchor in the goto call)
            base_url = f"{SOFASCORE_BASE}/{team_slug}/{team_id}"
            print("Loading page...")
            try:
                page.goto(base_url, wait_until="networkidle", timeout=60000)
            except Exception as e:
                print(f"Warning: Page load had issues: {e}")

            time.sleep(delay)

            # Navigate to players tab
            print("Navigating to players tab...")
            page.goto(url, wait_until="networkidle", timeout=30000)
            time.sleep(delay)

            # Extract player data from __NEXT_DATA__ JSON embedded in the page
            print("Extracting player data from page...")
            content = page.content()
            players = _parse_next_data_players(content)

            if not players:
                print("Warning: No players found in __NEXT_DATA__, trying HTML fallback...")
                soup = BeautifulSoup(content, "html.parser")
                players = _parse_squad_from_html(soup)

            browser.close()

    except Exception as e:
        print(f"Error using Playwright: {e}")
        import traceback

        traceback.print_exc()
        return []

    return players


def fetch_sofascore_squad_with_selenium(
    team_slug: str,
    team_id: int | None = None,
    *,
    delay: float = 1.0,
    chromedriver_path: str = "/usr/local/bin/chromedriver",
) -> list[dict[str, Any]]:
    """Fetch squad data using Selenium with ChromeDriver.

    This is an alternative to Playwright.

    Parameters
    ----------
    team_slug : str
        The URL slug for the team (e.g., "chelsea").
    team_id : int, optional
        The SofaScore team ID (e.g., 8418 for Chelsea).
    delay : float
        Seconds to wait after page load.
    chromedriver_path : str
        Path to ChromeDriver executable.

    Returns
    -------
    list[dict[str, Any]]
        List of player dicts.

    Requirements
    -----
    1. Install Selenium: pip install selenium
    2. Download ChromeDriver: https://chromedriver.chromium.org/
    """
    try:
        from selenium import webdriver
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support import expected_conditions as EC
        from selenium.webdriver.support.ui import WebDriverWait
    except ImportError:
        print("Selenium is not installed. Install it with:")
        print("  pip install selenium")
        print("Download ChromeDriver: https://chromedriver.chromium.org/")
        return []

    players = []

    # Construct URL
    if team_id:
        url = f"{SOFASCORE_BASE}/{team_slug}/{team_id}"
    else:
        url = f"{SOFASCORE_BASE}/{team_slug}"

    print(f"Launching Chrome to fetch: {url}")

    try:
        options = webdriver.ChromeOptions()
        options.add_argument("--headless")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument(f"user-agent={HEADERS['User-Agent']}")

        driver = webdriver.Chrome(chromedriver_path, options=options)

        print("Loading page (this may take 10-30 seconds)...")
        driver.get(url)

        # Wait for squad container to load
        try:
            WebDriverWait(driver, 15).until(
                EC.presence_of_all_elements_located((By.CLASS_NAME, "player"))
            )
        except Exception:
            print("Warning: Could not wait for squad container.")

        time.sleep(delay)

        # Extract HTML
        content = driver.page_source
        soup = BeautifulSoup(content, "html.parser")

        players = _parse_squad_from_html(soup)

        driver.quit()

    except Exception as e:
        print(f"Error using Selenium: {e}")
        return []

    return players
