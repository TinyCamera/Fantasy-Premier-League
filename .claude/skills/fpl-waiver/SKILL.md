---
name: fpl-waiver
description: Place, stage or cancel an FPL Draft waiver claim or free-agent signing for the Token Effort squad - claiming a player off the wire, dropping a player, or proposing a trade. Use when asked to "get", "claim", "sign", "pick up", "drop" or "waiver" a player, or to check who is available in the Canadian Exiles league.
---

# FPL Draft Waiver Claims

League: Canadian Exiles (id 38198). My entry: Token Effort (id 268479).

## Check availability first — never guess from board rank

Board rank says nothing about whether a player is *free*. 105 of 564 are owned.

```bash
python3 league_status.py --free FWD     # free agents at a position, by VOR
python3 league_status.py --squad all    # who owns whom
```

Guessing availability from `draft_board.csv` alone has already produced wrong
advice once (Isak, Brobbey and Rutter were all recommended while owned).

## The squad-shape lock — the thing that surprises people

FPL Draft squads are **exactly 2 GK / 5 DEF / 5 MID / 3 FWD** (`select_*` in the
draft API's `bootstrap-static` settings). There is no flex slot.

**A claim therefore forces a drop at the same position.** Signing a forward means
dropping one of your three forwards — the UI will not offer you anyone else.
Work out who the drop is *before* proposing the move, and say so up front; the
drop is usually the real decision, not the claim.

## Timing

- **Transaction deadline** is roughly 24h before the gameweek deadline —
  shown at the top of the Transactions page (e.g. Thu 27 Aug 10:30 GMT-7 for GW2).
- Claims are **waivers, not instant signings**: they process at that deadline and
  can be cancelled freely until then.
- Waiver priority is consumed when a claim succeeds, so a marginal claim has a
  cost beyond the dropped player.

## Placing a claim (browser)

Writes need authentication. `curl` gets `403 Authentication credentials were not
provided`; the session cookie is HttpOnly and cannot be extracted. The only route
is driving the user's already-signed-in Chrome session.

1. `navigate` to `https://draft.premierleague.com/team/transactions`
2. Screenshot to confirm they are signed in (header reads "Token Effort").
   If signed out, **stop and ask them to sign in** — never attempt to log in.
3. **Use `find` to get element refs, then click by `ref`.** Clicking the search
   box or the Sign button by coordinate silently does nothing on this page.
4. Type the player's surname into the search box; the table filters live.
5. Click **Sign** on the target row. The page navigates to
   `/team/transactions/remove` and lists the legal drops, each with a **Replace**
   button.
6. **STOP HERE.** Report the options with fixtures and projections, and get an
   explicit choice. Clicking **Replace** submits the claim.

To back out, click **Cancel** on the "You have requested to sign X" row. The page
returns to the transactions list showing `Proposed (0)`.

## Safety

- Every click lands as the user, immediately and for real.
- Never click **Replace**, **Cancel** on an existing pending claim, or any trade
  **Propose** / **Accept** without explicit confirmation in chat.
- Never attempt to sign in, and never handle the account password.
