#!/usr/bin/env python3
"""
Live view of the Canadian Exiles draft league, joined against draft_board.py.

The FPL Draft API answers these three endpoints without a login, so no MCP
server or session cookie is needed:

    /api/league/{id}/details          who is in the league
    /api/league/{id}/element-status   who owns every player  <- the important one
    /api/draft/{id}/choices           the full draft, pick by pick

`element-status` is what makes this useful: `owner: null` means free agent, so
the waiver wire can be listed exactly rather than guessed at.

    python3 league_status.py                # free agents, best first
    python3 league_status.py --free FWD     # free agents at one position
    python3 league_status.py --squad        # my squad
    python3 league_status.py --squad all    # every manager's squad
    python3 league_status.py --draft        # the draft, round by round

System Python's urllib has no working SSL certificates in this environment, so
every fetch shells out to curl.
"""

import argparse
import csv
import json
import os
import subprocess
import sys

LEAGUE_ID = 38198
MY_ENTRY = 268479          # "Token Effort" - the /entry/ id, not the league-entry id
BOARD = 'data/2026-27/draft_board.csv'

DRAFT_API = 'https://draft.premierleague.com/api/'
FPL_API = 'https://fantasy.premierleague.com/api/'

POS_ORDER = ['GK', 'DEF', 'MID', 'FWD']
SQUAD = {'GK': 2, 'DEF': 5, 'MID': 5, 'FWD': 3}


def fetch(url):
    out = subprocess.run(['curl', '-sf', url], capture_output=True)
    if out.returncode != 0:
        sys.exit(f"fetch failed: {url}")
    return json.loads(out.stdout)


def load():
    """Pull the league and join it to the projections."""
    details = fetch(f'{DRAFT_API}league/{LEAGUE_ID}/details')
    status = fetch(f'{DRAFT_API}league/{LEAGUE_ID}/element-status')
    boot = fetch(f'{FPL_API}bootstrap-static/')

    # league_entries carry two ids. element-status and draft/choices both key
    # off `entry_id` (the manager's FPL entry); `id` is a separate league-entry
    # id used by the standings, and is NOT what `owner` reports.
    managers = {}
    for e in details['league_entries']:
        if e.get('entry_id') is None:
            continue                       # the empty 8th slot
        managers[e['entry_id']] = e['entry_name']
    mine = MY_ENTRY

    owner = {s['element']: s['owner'] for s in status['element_status']}

    # draft_board.csv has no id column, but full_name is built from the same
    # first_name/second_name fields the API serves, so it joins cleanly.
    ids, live = {}, {}
    for e in boot['elements']:
        ids[(e['first_name'] + ' ' + e['second_name']).strip()] = e['id']
        live[e['id']] = e

    players = []
    with open(BOARD, newline='', encoding='utf-8') as fh:
        for r in csv.DictReader(fh):
            pid = ids.get(r['full_name'])
            if pid is None:
                continue
            e = live[pid]
            players.append({
                'id': pid,
                'name': r['name'],
                'pos': r['pos'],
                'team': r['team'],
                'rank': int(r['overall_rank']),
                'proj': int(r['projected']),
                'vor': int(r['vor']),
                'pp90': float(r['proj_pp90']),
                'flags': r['flags'],
                'owner': owner.get(pid),
                'status': e['status'],
                'news': e['news'],
            })
    return managers, mine, players


def fmt(p, show_owner=False):
    tail = f"  [{p['flags']}]" if p['flags'] else ''
    if p['status'] != 'a':
        tail += f"  !{p['news']}" if p['news'] else f"  !{p['status']}"
    return (f"  #{p['rank']:<4}{p['name'][:20]:22}{p['pos']:4}{p['team']:5}"
            f"proj {p['proj']:>4}{p['vor']:>+6} VOR{p['pp90']:>6.2f} pp90{tail}")


def show_free(players, pos=None, limit=25):
    pool = [p for p in players if p['owner'] is None]
    if pos:
        pool = [p for p in pool if p['pos'] == pos]
    pool.sort(key=lambda p: -p['vor'])
    print(f"\nFREE AGENTS{' - ' + pos if pos else ''} "
          f"({len(pool)} unowned{', top ' + str(limit) + ' shown' if len(pool) > limit else ''})")
    for p in pool[:limit]:
        print(fmt(p))


def show_squad(managers, mine, players, which):
    targets = sorted(managers) if which == 'all' else [mine]
    for owner_id in targets:
        squad = [p for p in players if p['owner'] == owner_id]
        squad.sort(key=lambda p: (POS_ORDER.index(p['pos']), -p['vor']))
        proj = sum(p['proj'] for p in squad)
        print(f"\n{managers[owner_id].upper()}  -  {len(squad)} players, {proj}pt projected")
        for pos in POS_ORDER:
            got = [p for p in squad if p['pos'] == pos]
            print(f"  {pos} ({len(got)}/{SQUAD[pos]})")
            for p in got:
                print('  ' + fmt(p))


def show_draft(managers, players):
    choices = fetch(f'{DRAFT_API}draft/{LEAGUE_ID}/choices')['choices']
    by_id = {p['id']: p for p in players}
    for c in sorted(choices, key=lambda c: c['index']):
        p = by_id.get(c['element'])
        who = managers.get(c['entry'], '?')
        label = f"{p['name']} ({p['pos']} {p['team']}) board #{p['rank']}" if p else str(c['element'])
        print(f"  R{c['round']:<3}pick {c['pick']:<3}{who[:22]:24}{label}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--free', nargs='?', const='', metavar='POS')
    ap.add_argument('--squad', nargs='?', const='mine', metavar='all')
    ap.add_argument('--draft', action='store_true')
    ap.add_argument('--limit', type=int, default=25)
    ap.add_argument('--root', default=os.path.dirname(os.path.abspath(__file__)))
    args = ap.parse_args()

    os.chdir(args.root)
    managers, mine, players = load()

    if args.draft:
        show_draft(managers, players)
    elif args.squad:
        show_squad(managers, mine, players, args.squad)
    else:
        pos = (args.free or '').upper() or None
        if pos and pos not in SQUAD:
            sys.exit('use: --free GK|DEF|MID|FWD')
        show_free(players, pos, args.limit)


if __name__ == '__main__':
    main()
