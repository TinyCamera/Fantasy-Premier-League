#!/usr/bin/env python3
"""
FPL Draft Board - builds a value-over-replacement ranked board for a draft league.

Raw points rank players against the whole league; a draft only cares how much
better a player is than the one you could still get at that position later.
That difference is VOR, and it is what makes an elite forward worth more than a
higher-scoring midfielder when forwards run out first.

Reads the season snapshot written by global_scraper.py. Stdlib only.

    python3 draft_board.py                 # 8 managers, default squad
    python3 draft_board.py --managers 10
    python3 draft_board.py --pos FWD
"""

import argparse
import csv
import glob
import os

SEASON = '2026-27'
DATA_SEASON = 'data/' + SEASON + '/'

POSITIONS = {'1': 'GK', '2': 'DEF', '3': 'MID', '4': 'FWD'}
SQUAD = {'GK': 2, 'DEF': 5, 'MID': 5, 'FWD': 3}

# Replacement level is set off the STARTING eleven, not the squad. Bench points
# do not score, so the player you are really choosing against is the worst
# starter at that position - not the last man drafted. Using squad slots breaks
# badly at goalkeeper: there are only 20 first-choice keepers, so in a 10-team
# league the 21st keeper is a career backup on ~20pt, which inflates every
# goalkeeper's VOR into the first round.
STARTERS = {'GK': 1, 'DEF': 4, 'MID': 4, 'FWD': 2}

# FPL availability codes. Anything not 'a' is a warning; 'u'/'n' means the
# player is not actually in the game right now (transferred abroad, unregistered).
STATUS_LABEL = {
    'a': '', 'd': 'DOUBT', 'i': 'INJ', 's': 'SUSP', 'u': 'GONE', 'n': 'NOT REG',
}
UNDRAFTABLE = {'u', 'n'}

TIER_GAP = 12          # points gap within a position that starts a new tier
UPSIDE_MIN_PP90 = 4.5  # scoring rate that makes a low-minutes season interesting
UPSIDE_MAX_MINS = 1800

# --- two-season projection ---------------------------------------------------
# One season of FPL points is noisy, and it badly misreads anyone who missed
# time. Blending 2024-25 in fixes both, but the two seasons are NOT on the same
# scoring system: defensive contribution points arrived in 2025-26, and the
# 2024-25 per-match files carry no defensive columns at all, so the points
# cannot be recomputed from scratch.
#
# Instead we rescale. These factors are the measured median pp90 ratio between
# the seasons for players with 1500+ minutes in both - i.e. how much the scoring
# change inflated each position. Defenders gained 27%; keepers, who cannot earn
# defensive contribution points, gained nothing, which is a good sanity check.
DEFCON_SCALE = {'GK': 1.00, 'DEF': 1.27, 'MID': 1.08, 'FWD': 0.93}

# Recency weight. Last season counts double.
SEASON_WEIGHT = {'2025/26': 1.0, '2024/25': 0.5}


def load_manual(root):
    """Hand-written estimates for players with no Premier League history.

    A player who has never played in the league cannot be projected from this
    repo's data at all, and leaving him on zero buries genuine draft options
    below several hundred squad fillers. These estimates fill that hole and are
    flagged MANUAL everywhere so they are never mistaken for modelled output.
    """
    path = os.path.join(root, 'manual_projections.csv')
    if not os.path.exists(path):
        return {}
    lines = [ln for ln in open(path) if not ln.lstrip().startswith('#')]
    return {r['id']: (int(r['projected']), r['rationale'])
            for r in csv.DictReader(lines)}


# FPL's web_name is a compressed display name ("B.Fernandes", "Virgil") while
# the strategy notes use the name people actually say. Expand where the common
# name is recoverable and fits the 20-char board column; known mononyms
# (Gabriel, Richarlison) and over-long names keep the short form.
MAX_NAME = 20

def display_name(web, first, second):
    first_words = first.split()
    if '.' in web:  # initials: rebuild from the real names
        cand = f"{first_words[0]} {second.split()[-1]}"
        return cand if len(cand) <= MAX_NAME else web
    if web == first:  # first name alone: append a short surname (van Dijk)
        cand = f"{first} {second}"
        return cand if len(second.split()) <= 2 and len(cand) <= MAX_NAME else web
    if web in first_words:  # "Thiago" for Igor Thiago
        return first if len(first) <= MAX_NAME else web
    if first_words and not web.startswith(first_words[0]):  # bare surname
        for prefix in (first, first_words[0]):
            cand = f"{prefix} {web}"
            if len(cand) <= MAX_NAME:
                return cand
    return web


def load_history(root):
    """Per-season Premier League history keyed by current player id.

    Gives us both the 2024-25 line used in the projection and a way to tell a
    returning player (Rashford, back from a loan abroad) apart from someone who
    has never played in the league at all."""
    hist = {}
    for path in glob.glob(os.path.join(root, 'players', '*', 'history.csv')):
        pid = os.path.basename(os.path.dirname(path)).rsplit('_', 1)[-1]
        hist[pid] = {row['season_name']: (int(row['total_points']),
                                          int(row['minutes']))
                     for row in csv.DictReader(open(path))}
    return hist


# A player absent from the league in 2024-25 has no 2024-25 data - which is not
# the same as having played and scored nothing. Averaging in that zero would
# punish every recent arrival (Sesko, Gyokeres, Ekitike) for the accident of
# having played abroad, so absent seasons are skipped rather than counted.
MINUTES_RECENCY = 0.75    # weight on last season when both seasons were played
ABSENT_DISCOUNT = 0.60    # haircut when a player missed all of last season


def project(pos, p25, m25, p24, m24):
    """Blend two seasons into an expected points total for 2026-27.

    Scoring rate and playing time are projected separately, because they fail in
    different ways. The rate is weighted by the minutes behind it, so a full
    2025-26 swamps the older season while a 600-minute one leans on 2024-25.
    Minutes lean hard on last season, which is the best evidence of a player's
    current role and fitness.
    """
    p24 *= DEFCON_SCALE[pos]                      # onto 2025-26 scoring
    w25, w24 = SEASON_WEIGHT['2025/26'], SEASON_WEIGHT['2024/25']
    wm25, wm24 = m25 * w25, m24 * w24
    if wm25 + wm24 == 0:
        return 0.0, 0, 0

    pp90 = (p25 * w25 + p24 * w24) / ((wm25 + wm24) / 90)

    if m25 and m24:
        # 2024-25 may only revise playing time UPWARD. The case we need it for
        # is the injury-shortened season (Isak: 694 minutes after 2758), where
        # it correctly restores a starter's workload. The reverse - dragging
        # someone down because he was on a bench two years ago - just punishes
        # players who have since won a starting role (Dewsbury-Hall went from 18
        # points at Chelsea to 151 as an Everton starter), and last season is
        # the better evidence of a player's role now.
        minutes = max(m25, MINUTES_RECENCY * m25 + (1 - MINUTES_RECENCY) * m24)
    elif m25:
        minutes = m25                             # no 2024-25 to say otherwise
    else:
        minutes = m24 * ABSENT_DISCOUNT            # away all last season

    return round(pp90, 2), round(minutes), round(pp90 * minutes / 90)


def load_players(root, seasons=2):
    """Join last season's finals onto the current player list.

    cleaned_players.csv and players_raw.csv are written from the same element
    list in the same order, so they join on row index. Verified before use.
    """
    cleaned = list(csv.DictReader(open(os.path.join(root, 'cleaned_players.csv'))))
    raw = list(csv.DictReader(open(os.path.join(root, 'players_raw.csv'))))
    if len(cleaned) != len(raw):
        raise SystemExit(f'row count mismatch: cleaned={len(cleaned)} raw={len(raw)} '
                         '- re-run global_scraper.py')
    for c, r in zip(cleaned, raw):
        if (c['first_name'], c['second_name']) != (r['first_name'], r['second_name']):
            raise SystemExit('cleaned_players.csv and players_raw.csv are out of order '
                             '- cannot join safely')

    teams = {t['id']: t['short_name']
             for t in csv.DictReader(open(os.path.join(root, 'teams.csv')))}
    hist = load_history(root)
    manual = load_manual(root)

    players = []
    for c, r in zip(cleaned, raw):
        mins = int(c['minutes'])
        pts = int(c['total_points'])
        pos = POSITIONS[r['element_type']]
        hist_seasons = hist.get(r['id'], {})
        p24, m24 = hist_seasons.get('2024/25', (0, 0)) if seasons >= 2 else (0, 0)
        proj_pp90, proj_mins, proj = project(pos, pts, mins, p24, m24)
        # A manual estimate only applies where the data genuinely says nothing.
        est, rationale = manual.get(r['id'], (0, ''))
        is_manual = bool(est) and proj == 0
        if is_manual:
            proj = est
        # Best earlier PL season, for the RETURN flag.
        prior_pts, prior_season = 0, None
        for s, (sp, _sm) in hist_seasons.items():
            if s != '2025/26' and sp > prior_pts:
                prior_pts, prior_season = sp, s
        players.append({
            'id': r['id'],
            'name': display_name(r['web_name'], c['first_name'], c['second_name']),
            'full_name': f"{c['first_name']} {c['second_name']}".strip(),
            'pos': pos,
            'team': teams.get(r['team'], '?'),
            'pts': pts,
            'mins': mins,
            'goals': int(c['goals_scored']),
            'assists': int(c['assists']),
            'clean_sheets': int(c['clean_sheets']),
            'bonus': int(c['bonus']),
            'pp90': round(pts / (mins / 90), 2) if mins else 0.0,
            # Price is irrelevant in a draft, but FPL sets it from their own
            # expected-returns model - the only quality signal we have for a
            # player with no Premier League history.
            'cost': int(r['now_cost']) / 10,
            'pts24': p24,
            'mins24': m24,
            'proj': proj,
            'proj_pp90': proj_pp90,
            'proj_mins': proj_mins,
            'prior_pts': prior_pts,
            'prior_season': prior_season,
            'manual': is_manual,
            'rationale': rationale if is_manual else '',
            'status': r['status'],
            'news': r['news'],
        })
    return players


def flags_for(p):
    f = []
    label = STATUS_LABEL.get(p['status'], p['status'].upper())
    if label:
        f.append(label)
    if p['manual']:
        f.append('MANUAL')       # estimate, not modelled from data
    if p['mins'] == 0 and p['mins24'] == 0:
        # Nothing in either season. Someone with older PL seasons (back from a
        # loan) is a very different bet from a true newcomer.
        f.append(f"RETURN {p['prior_pts']}pt" if p['prior_pts'] else 'NEW')
    elif p['proj_mins'] <= UPSIDE_MAX_MINS and p['proj_pp90'] >= UPSIDE_MIN_PP90:
        # Scores well when he plays, but the projection can't promise minutes.
        f.append('UPSIDE')
    return f


def build_board(players, managers):
    """Attach VOR and tier to every draftable player.

    Replacement level is the worst player at a position who would still be
    starting somewhere in the league - what you can comfortably wait for.
    """
    draftable = [p for p in players if p['status'] not in UNDRAFTABLE]

    replacement = {}
    for pos, per_team in STARTERS.items():
        pool = sorted((p for p in draftable if p['pos'] == pos),
                      key=lambda p: -p['proj'])
        idx = managers * per_team
        replacement[pos] = pool[idx]['proj'] if idx < len(pool) else 0

    for p in draftable:
        p['vor'] = p['proj'] - replacement[p['pos']]
        p['flags'] = flags_for(p)

    for pos in SQUAD:
        pool = sorted((p for p in draftable if p['pos'] == pos), key=lambda p: -p['proj'])
        # Only tier players who beat replacement. Below that the gaps between
        # adjacent players are always under the threshold, so everyone would
        # collapse into one meaningless tier of a couple of hundred names.
        tier = 1
        for i, p in enumerate(pool):
            p['pos_rank'] = i + 1
            if p['vor'] <= 0:
                p['tier'] = 0          # below replacement - not worth tiering
                continue
            if i and pool[i - 1]['proj'] - p['proj'] >= TIER_GAP:
                tier += 1
            p['tier'] = tier

    return draftable, replacement


def fmt_row(rank, p):
    flags = ' '.join(p['flags'])
    prev = f"{p['pts']:>4}/{p['pts24']:<4}"       # 2025-26 / 2024-25 actuals
    return (f"{rank:>3}. {p['name'][:20]:20} {p['pos']:3} {p['team']:4} "
            f"proj {p['proj']:>4} {p['vor']:>+5} VOR  T{p['tier']:<2} "
            f"{prev} {p['proj_pp90']:>5} pp90 {p['proj_mins']:>4}m  {flags}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--managers', type=int, default=8)
    ap.add_argument('--pos', choices=list(SQUAD), help='show one position only')
    ap.add_argument('--top', type=int, default=60)
    ap.add_argument('--root', default=DATA_SEASON)
    ap.add_argument('--seasons', type=int, choices=[1, 2], default=2,
                    help='1 = last season only, 2 = blend 2024-25 in (default)')
    args = ap.parse_args()

    players = load_players(args.root, args.seasons)
    board, replacement = build_board(players, args.managers)

    print(f"\nFPL DRAFT BOARD {SEASON}  -  {args.managers} managers, "
          f"{args.managers * 15} players drafted")
    print("Projection: 2025-26 and 2024-25 blended, minutes-weighted, with "
          "2024-25 rescaled onto the current scoring system.")
    print("VOR = projected points above the worst starter at that position.")
    print("Replacement level: " + '  '.join(
        f"{pos} {replacement[pos]}pt" for pos in ('GK', 'DEF', 'MID', 'FWD')))
    print("Flags: NEW = no PL minutes last season (unpriced). "
          "UPSIDE = strong per-90 in limited minutes.\n")

    if args.pos:
        pool = sorted((p for p in board if p['pos'] == args.pos), key=lambda p: -p['vor'])
        print(f"--- {args.pos} ---")
        last_tier = None
        for i, p in enumerate(pool[:args.top], 1):
            if p['tier'] != last_tier:
                print(f"  -- Tier {p['tier']} --")
                last_tier = p['tier']
            print(fmt_row(i, p))
    else:
        overall = sorted(board, key=lambda p: -p['vor'])
        for i, p in enumerate(overall[:args.top], 1):
            print(fmt_row(i, p))

    out = os.path.join(args.root, 'draft_board.csv')
    with open(out, 'w', newline='') as fh:
        w = csv.writer(fh)
        w.writerow(['overall_rank', 'name', 'full_name', 'pos', 'team', 'pos_rank',
                    'tier', 'projected', 'vor', 'proj_pp90', 'proj_minutes',
                    'points_2025_26', 'minutes_2025_26', 'pp90_2025_26',
                    'points_2024_25', 'minutes_2024_25', 'goals', 'assists',
                    'clean_sheets', 'bonus', 'cost', 'status', 'flags', 'news'])
        for i, p in enumerate(sorted(board, key=lambda p: -p['vor']), 1):
            w.writerow([i, p['name'], p['full_name'], p['pos'], p['team'], p['pos_rank'],
                        p['tier'], p['proj'], p['vor'], p['proj_pp90'], p['proj_mins'],
                        p['pts'], p['mins'], p['pp90'], p['pts24'], p['mins24'],
                        p['goals'], p['assists'], p['clean_sheets'], p['bonus'],
                        p['cost'], p['status'], ' '.join(p['flags']), p['news']])
    print(f"\nWrote {out} ({len(board)} draftable players)")


if __name__ == '__main__':
    main()
