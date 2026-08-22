---
name: fpl-gameweek
description: Weekly in-season FPL Draft routine for the Token Effort squad - check squad news and injuries, review the waiver wire, pick the starting XI, and review gameweek results. Use when asked about the upcoming deadline, who to start or bench, whether any players are flagged, what happened last gameweek, or for general "check my team" requests during the season.
---

# FPL Draft Gameweek Routine

League: Canadian Exiles (id 38198), **head-to-head scoring**, 7 managers.
My entry: Token Effort (id 268479).

## The week has two deadlines, not one

| | |
|---|---|
| **Transaction deadline** | ~Thu 10:30 America/Vancouver — waivers process |
| **Gameweek deadline** | ~Fri 10:30 America/Vancouver — lineup locks |

Both are shown live on the site; don't hardcode them. Waiver decisions are due a
full day before the lineup does, so a "wait for more news" plan often runs out of
road earlier than expected.

## 1. Pull the squad

```bash
python3 league_status.py --squad      # my 15, with projections and flags
python3 league_status.py --free       # best unowned players by VOR
```

## 2. Check for news — and don't trust `status` alone

`league_status.py` surfaces the FPL `status` / `news` fields, but **those track
fitness only**. A player can be `status=a` with empty news while actively agreeing
personal terms with another club.

This has already cost real information once: Watkins read as fully available on
21 Aug 2026 while he had agreed terms with Al-Hilal, Villa had rejected a £45m
bid, and Emery had said publicly he might not play.

So for any player who is a meaningful part of the squad, **web-search the name**
before the deadline rather than reading the flag and moving on. Watch for:

- transfer interest, especially Saudi Pro League — that window closes **later**
  than the Premier League's (12 Oct in 2026), so exit risk outlives the PL deadline
- a manager's press conference wording softening ("I don't want to sell him, but…")
- the club signing or being linked with a direct replacement — the strongest tell

A player sold out of the Premier League is **removed from the game**. In a draft
league that is a total loss with no transfer value recovered, which is why exit
risk deserves more weight here than in classic FPL.

## 3. Set the XI

11 starters from 15, and the shape is constrained:

- exactly **1 GK**
- **3–5 DEF**, **2–5 MID**, **1–3 FWD**
- bench slot 12 is locked to the reserve keeper
- **no captain** — `captains_disabled` is set in this league, so there is no
  multiplier and no captaincy decision to make

## 4. Head-to-head changes what "best" means

Scoring is H2H, so the table position depends on weekly matchups, not the season
total. Against a much stronger opponent, variance is your friend — a differential
with a high ceiling beats a safe floor. Against a weaker one, take the floor.
Check the fixture before optimising purely for expected points.

## Related

- Claiming or dropping players: use the **fpl-waiver** skill.
- Ranking methodology and VOR: use the **fpl-draft-prep** skill.
