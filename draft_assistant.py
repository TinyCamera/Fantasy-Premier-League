#!/usr/bin/env python3
"""
FPL Draft Assistant - live draft helper.

Tracks who has gone off the board, what you still need, and what to take next.
Ranking comes from draft_board.py (value over replacement) rather than raw
points, because in a draft the only thing that matters is how much better a
player is than whoever you could still get at that position later.

    python3 draft_assistant.py
    python3 draft_assistant.py --managers 10
"""

import argparse
import readline  # noqa: F401  - gives arrow-key history at the prompt

from draft_board import (
    DATA_SEASON, SQUAD, SEASON, build_board, load_players,
)

POS_ORDER = ['GK', 'DEF', 'MID', 'FWD']


class DraftAssistant:
    def __init__(self, managers=8, root=DATA_SEASON):
        players = load_players(root)
        self.board, self.replacement = build_board(players, managers)
        self.by_id = {p['id']: p for p in self.board}
        self.managers = managers
        self.gone = set()                       # ids off the board
        self.squad = {pos: [] for pos in POS_ORDER}

        print(f"\nFPL DRAFT ASSISTANT  {SEASON}  -  {managers} managers")
        print(f"{len(self.board)} draftable players loaded")
        print("Squad targets: " + ', '.join(f'{n} {p}' for p, n in SQUAD.items()))
        print("Replacement level: " + '  '.join(
            f"{p} {self.replacement[p]}pt" for p in POS_ORDER))

    # ---------- lookup ----------

    def resolve(self, query):
        """Find one player by name. Exact web_name wins, then whole-word, then
        substring - so 'Wood' finds Wood, not Hinshelwood."""
        q = query.strip().lower()
        if not q:
            return None
        pool = [p for p in self.board if p['id'] not in self.gone]

        exact = [p for p in pool if p['name'].lower() == q]
        if len(exact) == 1:
            return exact[0]

        word = [p for p in pool
                if q in p['name'].lower().split() or q in p['full_name'].lower().split()]
        if len(word) == 1:
            return word[0]

        sub = [p for p in pool
               if q in p['name'].lower() or q in p['full_name'].lower()]
        candidates = exact or word or sub
        if len(candidates) == 1:
            return candidates[0]
        if not candidates:
            print(f"  no available player matching '{query}'")
            return None

        print(f"  '{query}' is ambiguous:")
        for p in sorted(candidates, key=lambda p: -p['vor'])[:8]:
            print(f"    {p['name']} ({p['full_name']}) {p['pos']} {p['team']} "
                  f"proj {p['proj']}")
        print("  be more specific")
        return None

    def available(self, pos=None):
        pool = [p for p in self.board if p['id'] not in self.gone]
        if pos:
            pool = [p for p in pool if p['pos'] == pos]
        return sorted(pool, key=lambda p: -p['vor'])

    # ---------- draft actions ----------

    def mark_drafted(self, query):
        p = self.resolve(query)
        if not p:
            return
        self.gone.add(p['id'])
        print(f"  OFF THE BOARD: {p['full_name']} ({p['pos']} {p['team']}) "
              f"proj {p['proj']}  VOR {p['vor']:+d}")
        self._cliff_warning(p['pos'])

    def pick(self, query):
        p = self.resolve(query)
        if not p:
            return
        pos = p['pos']
        if len(self.squad[pos]) >= SQUAD[pos]:
            print(f"  squad already full at {pos} ({SQUAD[pos]}/{SQUAD[pos]})")
            return
        if p['flags']:
            print(f"  note: {p['full_name']} is flagged {' '.join(p['flags'])}"
                  + (f" - {p['news']}" if p['news'] else ""))
        self.gone.add(p['id'])
        self.squad[pos].append(p)
        print(f"  PICKED: {p['full_name']} ({pos} {p['team']}) "
              f"proj {p['proj']}  VOR {p['vor']:+d}")
        self.show_needs(brief=True)

    def undo(self, query):
        p = self.resolve_gone(query)
        if not p:
            return
        self.gone.discard(p['id'])
        for pos in POS_ORDER:
            self.squad[pos] = [x for x in self.squad[pos] if x['id'] != p['id']]
        print(f"  restored {p['full_name']} to the board")

    def resolve_gone(self, query):
        q = query.strip().lower()
        hits = [p for p in self.board if p['id'] in self.gone
                and (q in p['name'].lower() or q in p['full_name'].lower())]
        if len(hits) == 1:
            return hits[0]
        print(f"  could not uniquely find a drafted player matching '{query}'")
        return None

    # ---------- views ----------

    def show_best(self, pos=None, limit=12):
        pool = self.available(pos)
        head = f"BEST AVAILABLE{' ' + pos if pos else ''}"
        print(f"\n{head}")
        for i, p in enumerate(pool[:limit], 1):
            flags = ' '.join(p['flags'])
            print(f"{i:>3}. {p['name'][:20]:20} {p['pos']:3} {p['team']:4} "
                  f"proj {p['proj']:>4} {p['vor']:>+5} VOR  T{p['tier']:<2} "
                  f"{p['proj_pp90']:>5} pp90  {flags}")

    def show_tiers(self, pos, limit=16):
        pool = self.available(pos)
        print(f"\n{pos} TIERS (available only)")
        last = None
        for p in pool[:limit]:
            if p['tier'] != last:
                remaining = sum(1 for x in pool if x['tier'] == p['tier'])
                label = f"Tier {p['tier']}" if p['tier'] else "Below replacement"
                print(f"  -- {label} ({remaining} left) --")
                last = p['tier']
            print(f"     {p['name'][:20]:20} {p['team']:4} proj {p['proj']:>4} "
                  f"{p['vor']:>+5} VOR  {' '.join(p['flags'])}")

    def show_squad(self):
        print("\nYOUR SQUAD")
        total = 0
        for pos in POS_ORDER:
            got = self.squad[pos]
            total += len(got)
            print(f"  {pos} ({len(got)}/{SQUAD[pos]})")
            for p in got:
                print(f"     {p['full_name'][:28]:28} {p['team']:4} proj {p['proj']:>4} "
                      f"{p['vor']:>+5} VOR")
        pts = sum(p['proj'] for pos in POS_ORDER for p in self.squad[pos])
        vor = sum(p['vor'] for pos in POS_ORDER for p in self.squad[pos])
        print(f"  total {total}/15  -  {pts}pt projected, {vor:+d} VOR")

    def show_needs(self, brief=False):
        need = {pos: SQUAD[pos] - len(self.squad[pos]) for pos in POS_ORDER}
        line = '  '.join(f'{pos} {n}' for pos, n in need.items() if n)
        print(f"  still need: {line or 'nothing - squad complete'}")
        return need

    # ---------- strategy ----------

    def _cliff_warning(self, pos):
        """Warn when a position is one pick away from losing a tier."""
        pool = self.available(pos)
        if not pool:
            return
        top_tier = pool[0]['tier']
        left = sum(1 for p in pool if p['tier'] == top_tier)
        if left <= 2 and SQUAD[pos] - len(self.squad[pos]) > 0:
            nxt = next((p for p in pool if p['tier'] > top_tier), None)
            drop = pool[0]['proj'] - nxt['proj'] if nxt else 0
            print(f"  ** {pos} tier {top_tier} has {left} left - "
                  f"next tier is {drop}pt lower **")

    def recommend(self, n=5):
        """Best available you have room for, ranked by VOR, with a nudge toward
        positions that are about to fall off a cliff."""
        need = {pos: SQUAD[pos] - len(self.squad[pos]) for pos in POS_ORDER}
        openpos = [pos for pos in POS_ORDER if need[pos] > 0]
        if not openpos:
            print("\n  squad complete")
            return

        pool = [p for p in self.available() if need[p['pos']] > 0]
        print("\nRECOMMENDATION")
        print(f"  need: " + '  '.join(f'{p} {need[p]}' for p in openpos))

        for i, p in enumerate(pool[:n], 1):
            same_tier = sum(1 for x in self.available(p['pos']) if x['tier'] == p['tier'])
            note = ''
            if same_tier <= 2:
                note = f"  <- only {same_tier} left in tier {p['tier']}"
            if p['flags']:
                note += f"  [{' '.join(p['flags'])}]"
            print(f"{i:>3}. {p['name'][:20]:20} {p['pos']:3} {p['team']:4} "
                  f"proj {p['proj']:>4} {p['vor']:>+5} VOR{note}")

        # positions where waiting is cheap vs expensive
        print("  waiting cost per position (VOR lost between best now and 6 picks later):")
        for pos in openpos:
            pool_p = self.available(pos)
            if len(pool_p) > 6:
                cost = pool_p[0]['vor'] - pool_p[6]['vor']
                print(f"     {pos}: {cost:>3} VOR")


HELP = """
COMMANDS
  drafted <player>   someone else took him
  pick <player>      you took him
  undo <player>      put him back on the board
  best [POS]         best available (optionally GK/DEF/MID/FWD)
  tiers <POS>        tier breakdown for a position
  recommend          what to take next
  squad              your squad so far
  help / quit
"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--managers', type=int, default=8)
    ap.add_argument('--root', default=DATA_SEASON)
    args = ap.parse_args()

    a = DraftAssistant(args.managers, args.root)
    print(HELP)

    while True:
        try:
            raw = input("\n> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\ngood luck")
            return
        if not raw:
            continue
        cmd, _, arg = raw.partition(' ')
        cmd, arg = cmd.lower(), arg.strip()

        try:
            if cmd in ('quit', 'exit'):
                print("good luck")
                return
            elif cmd == 'help':
                print(HELP)
            elif cmd == 'drafted':
                a.mark_drafted(arg)
            elif cmd == 'pick':
                a.pick(arg)
            elif cmd == 'undo':
                a.undo(arg)
            elif cmd == 'best':
                pos = arg.upper() if arg else None
                if pos and pos not in SQUAD:
                    print("  use: best GK|DEF|MID|FWD")
                else:
                    a.show_best(pos)
            elif cmd == 'tiers':
                pos = arg.upper()
                if pos not in SQUAD:
                    print("  use: tiers GK|DEF|MID|FWD")
                else:
                    a.show_tiers(pos)
            elif cmd == 'recommend':
                a.recommend()
            elif cmd == 'squad':
                a.show_squad()
                a.show_needs()
            else:
                print("  unknown command - type help")
        except Exception as exc:
            print(f"  error: {exc}")


if __name__ == '__main__':
    main()
