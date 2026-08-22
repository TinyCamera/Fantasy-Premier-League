---
name: fpl-draft-prep
description: Prepare for the annual FPL draft - build the ranked draft board, generate the printable cheat sheet, run the live draft assistant, and apply the VOR-based draft strategy. Use when drafting a new season's squad, discussing draft rankings, value over replacement, tiers, replacement level, or manual projections for players with no Premier League history.
---

# FPL Draft Preparation

Dormant most of the year. The 2026-27 draft ran 17 Aug 2026; the next one is
around August 2027. Everything below was written against the 2026-27 draft and
should be re-derived, not trusted, once a new season's data lands.

## Before anything else

Refresh the season snapshot **before the GW1 deadline**. The FPL API serves the
previous season's final totals pre-season and zeroes them at the deadline, so a
late snapshot loses the entire basis of the ranking. See "Data Refresh" in
CLAUDE.md.

## Tooling

### Draft Board Generator
`draft_board.py` builds the ranked board and writes `data/2026-27/draft_board.csv`.
Stdlib only — no pandas needed.

```bash
python3 draft_board.py                # top 60 overall, 8 managers
python3 draft_board.py --pos FWD      # one position, with tier breaks
python3 draft_board.py --managers 10  # different league size
```

`make_draft_sheet.py` renders the same board as a printable/browsable HTML cheat
sheet at `reports/draft_sheet.html` (click a row to strike a player off).

```bash
python3 make_draft_sheet.py
```

### Live Draft Helper Tool
Use `draft_assistant.py` for live draft support. It imports its ranking from
`draft_board.py`, so both stay consistent.

#### Starting the Assistant
```bash
python3 draft_assistant.py
python3 draft_assistant.py --managers 10
```

#### Key Commands During Draft
- `drafted [player]` - Mark player as drafted by someone else
- `pick [player]` - Add player to your squad
- `undo [player]` - Put a player back on the board
- `best` / `best [pos]` - Best available by VOR
- `recommend` - Best available you have room for, plus waiting cost per position
- `squad` - Show current squad composition and needs
- `tiers [pos]` - Tier breakdown, counting only players still available

#### Alternative: Direct Chat Commands
Instead of running the script, just tell Claude:
- "Salah was just drafted"
- "Show me best available forwards"
- "Who should I pick next?"
- "What's my squad looking like?"

### Draft Strategy (2026-27, built on 2025-26 final data)

Ranking is **value over replacement (VOR)** on a **two-season projection**, not
raw points. In a draft the only thing that matters is how much better a player
is than whoever you could still get at that position later.

#### The projection
2025-26 and 2024-25 are blended, but they are **not on the same scoring system** —
defensive contribution points arrived in 2025-26, and the 2024-25 per-match files
carry no defensive columns at all, so the old points cannot be recomputed. Instead
2024-25 is rescaled by the measured median pp90 ratio per position (`DEFCON_SCALE`):

| Pos | Scale | Reading |
|-----|-------|---------|
| DEF | ×1.27 | DefCon added 27% to defender scoring |
| MID | ×1.08 | only ball-winners clear the 12-action threshold |
| GK  | ×1.00 | DefCon does not apply to keepers — a good sanity check |
| FWD | ×0.93 | forwards almost never hit the threshold |

Rate and playing time are projected separately because they fail differently:
- **Rate** is weighted by the minutes behind each season, so a full 2025-26
  swamps the older year while a 600-minute one leans on 2024-25.
- **Minutes** lean on last season and 2024-25 may only revise them *upward*.
  That asymmetry is deliberate: it rescues the injury-shortened season (Isak,
  694 minutes after 2758) without punishing someone who has since won a starting
  role (Dewsbury-Hall went 18pt on Chelsea's bench → 151pt as an Everton starter).

Run `--seasons 1` to fall back to last season only and compare.

Replacement level is set off the **starting eleven** (`STARTERS` in
`draft_board.py`, a 1/4/4/2 shape), not squad slots. Bench points don't score, so
the real alternative is the worst starter at that position. Using squad slots
breaks at goalkeeper — there are only 20 first-choice keepers, so in a 10-team
league the 21st is a career backup on ~20pt, which inflates every GK into round 1.

Replacement level, 8-manager league (worst *starter* at each position):

| Pos | Replacement | Meaning |
|-----|-------------|---------|
| FWD | **95pt** | the 16th forward — the floor drops out here |
| DEF | 113pt | the 32nd defender |
| GK  | 120pt | the 8th keeper |
| MID | 126pt | the 32nd midfielder — highest floor, so waiting is free |

#### Top of the board by projected VOR
1. **Haaland (FWD, MCI)** — proj 221, **+126 VOR**. The only automatic pick.
2. **Bruno Fernandes (MID, MUN)** — proj 220, +94
3. **Igor Thiago (FWD, BRE)** — proj 181, +86
4. **Gabriel (DEF, ARS)** — proj 198, +85
5. **Watkins (FWD, AVL)** — proj 174, +79
6. **João Pedro (FWD, CHE)** — proj 172, +77
7. **Semenyo (MID, MCI)** — proj 194, +68
8. **Virgil van Dijk (DEF, LIV)** — proj 179, +66

**The board's shape: a few players, then a plateau.** Ranks 4-24 span only 48
points of VOR. Every position is one elite player then a long flat tier
(MID 30 deep, DEF 30, FWD 12, GK all 8 in one tier). After the early rounds,
positional scarcity should drive picks rather than the overall ranking.

#### Positional urgency (most → least)
1. **Top 4** — Haaland, Bruno, Thiago, Gabriel. Take whoever is there.
2. **FORWARDS** — get two of the top four. 4th forward proj 172, 6th 128, replacement 95.
3. **DEFENDERS** — after Gabriel it is one broad tier of 30. Let them come to you.
4. **MIDFIELDERS** — deepest position, highest replacement. Never reach.
5. **GOALKEEPERS** — Raya (+35) or wait. All 8 startable keepers are one flat tier.

#### Squad Composition Target
- 2 GK, 5 DEF, 5 MID, 3 FWD (15 total)

#### Things that changed for 2026-27
- **Defensive contribution scoring** landed in 2025-26 and is baked into these
  totals. Centre-backs and ball-winning midfielders are worth far more than
  pre-2025-26 reasoning suggests (Gabriel went 117 → 209pt).
- **Gone from the league:** Salah, Trossard, Chris Wood, Dan Burn.
- **Promoted:** Coventry, Hull, Ipswich. **Relegated:** Burnley, West Ham, Wolves.
- **Big movers:** Semenyo/Guéhi/Elliot Anderson → Man City, João Pedro and
  Morgan Rogers → Chelsea, Isak → Liverpool, Senesi → Spurs.

#### Players with no data
190 players had no 2025-26 minutes. `data/2026-27/manual_projections.csv` holds
hand estimates for the 14 worth knowing about, applied **only** where the data is
silent (a player with real history keeps it) and flagged `MANUAL` everywhere.
Edit that file freely.

Working rule: **defensive output travels between leagues far better than
attacking output.** A midfielder's tackle and recovery volume carries over; his
expected goals mostly does not. So DefCon specialists are safer bets than
forwards arriving on a big continental goal tally.

Only two newcomers project into the drafted 120: **Gonzalo García** (FWD, FUL,
#68) and **Oli McBurnie** (FWD, HUL, #90). Everything else is waiver material.

Ipswich are a special case — they played in the PL in 2024-25, so adding that
season gives their squad real data rather than nothing (Leif Davis: 52pt/2742min).

#### Remaining weaknesses
- **Role changes.** The blend regresses anyone whose situation genuinely changed.
  The asymmetric minutes rule limits this, but judgement still beats the model
  when someone has clearly just won a starting job.
- `UPSIDE` — strong per-90 in limited minutes; projection can't promise minutes.
- `RETURN <n>pt` — no recent minutes but real PL pedigree (Rashford, Kulusevski).

