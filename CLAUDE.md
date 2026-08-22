# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Current FPL Team (2026-27)

**Team name: Token Effort** (manager: Niall Conroy)

**Drafted 17 Aug 2026** (pick 5 of 7 in the snake; league "Canadian Exiles",
draft league ID 38198, my entry ID 268479). Round drafted in parentheses.

- GKP: Kelleher BRE (7), Petrović BOU (15)
- DEF: Senesi TOT (4), Truffert BOU (5), Mitchell CRY (9), Van Hecke TOT (12), Keane EVE (14)
- MID: Gibbs-White NFO (3), Harry Wilson LEE (6), Elliot Anderson MCI (8), Mateus Fernandes TOT (11), Le Fée SUN (13)
- FWD: Watkins AVL (1), João Pedro CHE (2), Welbeck CHE (10)

Previous season's squad (2025-26) is in git history. Note that Salah, Trossard,
Chris Wood and Dan Burn all left the Premier League ahead of 2026-27.

### Squad risk watch

- **Watkins (FWD, AVL) — transfer risk, live as of 21 Aug 2026.** Agreed personal
  terms with Al-Hilal; Villa rejected a £45m bid on 20 Aug. Emery moved from "not
  selling" to "this can change... if I can replace him", and Villa are lining up
  **Nicolas Jackson** (CHE, FPL id 166) as the replacement. Emery said Watkins is
  unlikely to face Brighton in GW1. FPL still lists him `status=a` with no news.
  The **Saudi window closes 12 October**, so the risk runs to ~GW7, not to the
  PL deadline. In a draft league a sale is a total loss of a round-1 pick — no
  transfer value recovered — so the hedge is a trade while his name still carries
  round-1 weight with rivals. **Jackson is not on the wire** — Ciaran Kelly
  (No Place I'd Radebe) drafted him, which makes Ciaran the natural trade partner.
- **Welbeck (FWD, CHE)** — flagged 75% (unspecified injury) as of 21 Aug 2026.
  With Watkins also doubtful that leaves João Pedro as the only certain forward.

### League rivals (named so far)

| Team | Manager |
|------|---------|
| Iraola Coasters | Ross Lambert |
| Charli XGx | Nick L |
| Le Saux Solid Crew | Tom Marsh |
| Darlow IQ | Gerard Farrell |
| Token Effort | Niall Conroy |
| No Place I'd Radebe | Ciaran Kelly |
| On Amad One FC | Sangram Panag |

League created for 8 but only 7 managers joined and drafted; the 8th slot is empty.

## Live League Data (`league_status.py`)

The FPL **Draft** API serves these without any login, MCP server, or session
cookie — plain `curl` is enough:

| Endpoint | Gives you |
|---|---|
| `/api/league/38198/details` | managers, entry ids, draft metadata |
| `/api/league/38198/element-status` | **owner of every player** (`null` = free agent) |
| `/api/draft/38198/choices` | the whole draft, pick by pick |
| `/api/game` | current event, whether waivers have processed |

`league_status.py` joins those to `data/2026-27/draft_board.csv`, so the waiver
wire can be listed exactly rather than guessed at.

```bash
python3 league_status.py                # best free agents by VOR
python3 league_status.py --free FWD     # free agents at one position
python3 league_status.py --squad        # my squad
python3 league_status.py --squad all    # every manager's squad
python3 league_status.py --draft        # the draft, round by round
```

Two id gotchas, both already handled in the script:
- `league_entries` carries **two** ids. `element-status.owner` and
  `draft/choices.entry` key off **`entry_id`** (mine: 268479). The separate `id`
  field (mine: 270809) is used by the standings and is *not* the owner key.
- `draft_board.csv` has no id column, but its `full_name` is built from the same
  `first_name`/`second_name` the API serves, so it joins on name (564/564 match).

System Python's `urllib` has no working SSL certificates here, so the script
shells out to `curl` for every fetch.

### Reads are public, writes are not

Every endpoint above is **read-only and unauthenticated** — `league_status.py`
needs no cookie and would run fine from cron.

Writing (waiver claims, trades, lineup changes) is a different matter:

```
GET /api/draft/entry/268479/transactions   via curl     -> 403 "Authentication credentials were not provided."
GET /api/draft/entry/268479/transactions   via page JS  -> 200 {picks, trades, waivers, watchlist}
```

The only way writes have worked is by driving the **already-signed-in Chrome
session** through the browser tools — borrowed authority, not a held credential.
The session cookie (`pl_profile`) is **HttpOnly**: it does not appear in
`document.cookie`, so it cannot be lifted from the page. Confirmed JS-visible
cookies are guest/analytics only (`pl_guest_id`, `activeEntry`, OneTrust, Adobe).

Consequences: sign out, switch browser, or move to a phone and write access is
gone. Scripting a login is not an option worth pursuing — it needs the account
password (off-limits) and `users.premierleague.com/accounts/login/` sits behind
bot protection anyway.

## Repository Overview

This is a comprehensive Fantasy Premier League (FPL) historical dataset repository containing player statistics, gameweek data, and analysis scripts from the 2016-17 season through 2025-26. The repository is primarily designed for FPL data analysis, player research, and draft preparation.

## Key Data Structure

### Season Data Organization
- **Player Data**: `data/{season}/cleaned_players.csv` - Season overview stats for all players
- **Gameweek Data**: `data/{season}/gws/gw{number}.csv` - Individual gameweek performance data
- **Merged Data**: `data/{season}/gws/merged_gw.csv` - All gameweeks combined for a season
- **Individual Players**: `data/{season}/players/{player_name}/` - Player-specific historical data
- **Fixtures**: `data/{season}/fixtures.csv` - Fixture lists and results

### Key Files for Analysis
- `data/cleaned_merged_seasons.csv` - All seasons combined with historical performance data
- `data/cleaned_merged_seasons_team_aggregated.csv` - Team-level aggregated statistics
- `data/master_team_list.csv` - Master list of all teams across seasons
- Latest season data: `data/2025-26/` contains the most recent player data

## Core Scripts for Data Analysis

### Data Collection and Processing
```bash
# Get current FPL data and parse for current season
python global_scraper.py

# Download specific team data
python teams_scraper.py <team_id>

# Get top manager data
python top_managers.py

# Analyze top players by gameweek
python top_players.py
```

### Key Analysis Scripts
- `getters.py` - Functions to fetch data from FPL API (`get_data()`, `get_individual_player_data()`)
- `parsers.py` - Data parsing utilities (`parse_top_players()`, `extract_stat_names()`)
- `cleaners.py` - Data cleaning and preprocessing functions
- `utility.py` - General utility functions for data handling
- `collector.py` - Functions to collect and merge gameweek data
- `mergers.py` - Scripts to merge data across seasons
- `understat.py` - Integration with Understat expected stats data

## Environment Setup

### Dependencies
Install required packages:
```bash
pip install -r requirements.txt
```

Key dependencies: pandas, numpy, requests, beautifulsoup4

### Python Environment
The scripts are designed to work with Python 3.x and primarily use:
- `pandas` for data manipulation
- `requests` for API calls to FPL endpoints
- `csv` for data I/O operations

## Player Position Mapping
In the data files, `element_type` corresponds to positions:
- 1 = Goalkeeper (GK)
- 2 = Defender (DEF)  
- 3 = Midfielder (MID)
- 4 = Forward (FWD)

## Key Data Fields for Draft Analysis
- `total_points` - Season total points
- `now_cost` - Current price (in 0.1m units)
- `selected_by_percent` - Ownership percentage
- `minutes` - Total minutes played
- `goals_scored`, `assists` - Basic attacking stats
- `clean_sheets` - For defenders/goalkeepers
- `bonus` - Bonus points earned
- `ict_index` - Influence, Creativity, Threat composite metric
- `threat`, `creativity`, `influence` - Individual ICT components

## Draft Preparation Workflow
1. Load latest season data: `pd.read_csv('data/2025-26/cleaned_players.csv')`
2. Analyze historical performance: Use `data/cleaned_merged_seasons.csv`
3. Check fixture difficulty: Use `data/2025-26/fixtures.csv`
4. Compare players by position using `element_type` filtering
5. Consider `minutes`, `total_points`, and consistency metrics

## Data Analysis Patterns
- Filter by position: `df[df['element_type'] == 4]` for forwards
- Sort by value: `df.sort_values('total_points', ascending=False)`
- Calculate points per million: `df['total_points'] / (df['now_cost'] / 10)`
- Analyze consistency: Use gameweek data in `gws/` folders

## FPL Draft Assistant

The draft board (`draft_board.py`), printable cheat sheet (`make_draft_sheet.py`),
live draft helper (`draft_assistant.py`) and the whole VOR ranking methodology now
live in the **`fpl-draft-prep`** skill (`.claude/skills/fpl-draft-prep/`). It is
only needed once a year, so it loads on demand rather than every session.

## Skills (`.claude/skills/`)

Project-scoped, so they only apply inside this repo.

| Skill | Use it for |
|---|---|
| `fpl-gameweek` | the weekly routine — news, wire, starting XI, results |
| `fpl-waiver` | claiming, dropping or trading players via the browser |
| `fpl-draft-prep` | the annual draft: board, cheat sheet, VOR strategy |

## Notable Limitations
- GW35 expected points data may contain errors (all values = 0)
- Only major updates planned: season start, January window, season end

## Data Refresh

`global_scraper.py` (season is hardcoded, currently `2026-27`) pulls the full
season snapshot from the FPL API into `data/2026-27/`.

```bash
python3 global_scraper.py     # needs requests, pandas, beautifulsoup4
```

Two things worth knowing:
- **`data/{season}/cleaned_players.csv` holds the PREVIOUS season's final stats**,
  attached to each player's current club and current position. That is the whole
  basis of draft ranking. Pre-season the FPL API still serves last season's
  totals; it zeroes them at the GW1 deadline, so the snapshot must be taken
  before then or last season's numbers are only recoverable per-player from
  `element-summary`.
- `cleaned_players.csv` and `players_raw.csv` are written in the same row order,
  so they join on index. `draft_board.py` asserts this before relying on it.

System Python lacks `requests`/`pandas` and its `urllib` has no working SSL
certificates (use `curl` for ad-hoc API calls). Build a venv on Python 3.13:

```bash
python3.13 -m venv .venv && .venv/bin/pip install requests pandas beautifulsoup4
.venv/bin/python global_scraper.py
```
- whenever i meantion my team, or any updates ive made, remember my team. keep track of my current team in claude.md
- im playing a draft league, so the price of players doesnt matter to me