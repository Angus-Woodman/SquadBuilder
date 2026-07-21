# SofaScore Scraper Implementation

## Overview

I've created a new data source scraper for SofaScore (`backend/src/app/ingest/sofascore.py`) that can fetch Chelsea squad data using browser automation.

## Technical Implementation

### Data Source
SofaScore embeds player data in the `__NEXT_DATA__` JSON object within the HTML page. This data is extracted and parsed by:
1. Loading the team page with Playwright
2. Extracting the `__NEXT_DATA__` script from the page HTML
3. Parsing JSON and navigating to `pageProps.players.players`
4. Extracting player names, positions (F/M/D/G), and shirt numbers

### URL Pattern
The correct SofaScore URL pattern is:
```
https://www.sofascore.com/football/team/{team_slug}/{team_id}#tab:players
```

Where:
- `team_slug`: URL-friendly team name (e.g., "chelsea", "manchester-city")
- `team_id`: Numeric SofaScore team ID

Example: https://www.sofascore.com/football/team/chelsea/38#tab:players

### Browser Automation
The scraper uses **Playwright** (default) or **Selenium** to:
1. Load the page and render JavaScript
2. Wait for data to load
3. Extract the rendered HTML with embedded JSON
4. Parse player information from `__NEXT_DATA__`

## Installation

### 1. Playwright (Already Installed)
```bash
pip install playwright
playwright install chromium
```

### 2. Backend Integration
The scraper has been integrated into the CLI:

```bash
cd backend
python -m app.cli sofascore-squad --help
```

## Usage

### Basic Usage - Chelsea Squad
```bash
python -m app.cli sofascore-squad --team chelsea
```

Or with explicit team ID:
```bash
python -m app.cli sofascore-squad --team chelsea --team-id 38
```

### Options
- `--team`: Team slug (required, e.g., 'chelsea', 'manchester-city')
- `--team-id`: SofaScore team ID (optional, auto-lookup for common teams)
- `--use-playwright`: Use Playwright browser automation (default)
- `--use-selenium`: Use Selenium/ChromeDriver instead
- `--show-browser`: Show the browser window (Playwright only)
- `--delay`: Wait time after page load (default: 1.0 seconds)
- `--chromedriver`: Path to ChromeDriver (for Selenium)

### Common Team IDs & Slugs
- **chelsea**: `38`
- **manchester-city**: `17`
- **manchester-united**: `33`
- **liverpool**: `39`
- **arsenal**: `42`

*Need a different team? Visit https://www.sofascore.com/football/team/{team_slug} to find the team ID.*

## Example Output
```
Using Playwright browser automation...
Launching browser to fetch: https://www.sofascore.com/football/team/chelsea/38#tab:players
Loading page...
Navigating to players tab...
Extracting player data from page...

Found 37 players:

 1. Alejandro Garnacho             | Pos: F          | #: 49
 2. João Pedro                     | Pos: F          | #: 20
 3. Nicolas Jackson                | Pos: F          | #: 15
...
33. Robert Sánchez                 | Pos: G          | #: 1
34. Filip Jørgensen                | Pos: G          | #: 12
35. Gabriel Słonina                | Pos: G          | #: 44

Total: 37 players
```

## Files Created/Modified

### New Files
1. **`backend/src/app/ingest/sofascore.py`**
   - Main scraper module with three approaches:
     - `fetch_sofascore_squad()`: HTTP-only (shows why browser automation is needed)
     - `fetch_sofascore_squad_with_playwright()`: Browser automation (recommended)
     - `fetch_sofascore_squad_with_selenium()`: Selenium alternative

### Modified Files
1. **`backend/src/app/cli.py`**
   - Added `sofascore-squad` CLI command
   - Integrated with existing command structure

## Architecture

The scraper works in three steps:

1. **Load Page**: Playwright loads the SofaScore team page with JavaScript rendering
2. **Extract Team ID**: Gets the team ID from the page URL if not provided
3. **Fetch Data**: Attempts to fetch player data via:
   - Direct API call through browser context (preferred)
   - HTML parsing fallback (if API fails)

## Known Limitations

1. **Requires Team ID**: SofaScore URLs use numeric IDs, so you need to know the team ID
2. **Slow**: Playwright launches a full browser, which takes 10-30 seconds per request
3. **API Changes**: SofaScore may change their API structure without notice
4. **Rate Limiting**: Heavy scraping may trigger rate limiting

## Next Steps

### Integration with Database
To integrate SofaScore data into your player database:

```python
from app.ingest.sofascore import fetch_sofascore_squad_with_playwright
from app.db.store import upsert_players
from app.db.queries import list_players

# Fetch Chelsea squad
players = fetch_sofascore_squad_with_playwright("chelsea", team_id=8418)

# Transform and store
player_dicts = [
    {
        "player_id": hash(p["name"]),  # Generate ID if needed
        "name": p["name"],
        "position": p["position"],
        "shirt_number": p.get("shirt_number"),
        "club": "Chelsea",
    }
    for p in players
]

upsert_players(player_dicts)
```

### Alternative: Selenium Instead of Playwright
If you prefer Selenium:

```bash
pip install selenium
# Download ChromeDriver from https://chromedriver.chromium.org/
python -m app.cli sofascore-squad --team chelsea --team-id 8418 --use-selenium \
  --chromedriver /path/to/chromedriver
```

## Testing
Debug scripts created during development:
- `debug_sofascore.py`: Captures network requests
- `test_sofascore.py`: Tests URL resolution and API
- `inspect_valid_page.py`: Inspects page structure

## Troubleshooting

### "Playwright is not installed"
```bash
pip install playwright
playwright install chromium
```

### "No players found for team 'X'"
Try running with explicit team ID:
```bash
python -m app.cli sofascore-squad --team chelsea --team-id 38
```

### Slow performance
The scraper launches a full browser, which takes 15-30 seconds. This is normal. Increase wait time if needed:
```bash
python -m app.cli sofascore-squad --team chelsea --delay 5
```

### Want to see the browser loading?
Use `--show-browser` flag (Playwright only):
```bash
python -m app.cli sofascore-squad --team chelsea --show-browser
```

### Known limitation: Foreign/young players
SofaScore shows foreign players and youth academy players separately. The scraper fetches from the main `players` array first (37 for Chelsea). To include all players, the code could combine multiple arrays (`players`, `foreignPlayers`, `nationalPlayers`).

## Future Improvements

1. **Multi-team scraping**: Fetch multiple teams and their squads
2. **Team ID lookup**: Auto-discover team IDs from slugs
3. **Caching**: Store fetched data to avoid repeated requests
4. **Advanced parsing**: Extract more player data (age, contract, market value)
5. **Error handling**: Better error messages and retry logic
6. **Rate limiting**: Implement polite request spacing

## Resources

- [Playwright Documentation](https://playwright.dev/python/)
- [Selenium Documentation](https://www.selenium.dev/documentation/)
- [SofaScore Website](https://www.sofascore.com/)
