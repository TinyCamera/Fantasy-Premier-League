#!/usr/bin/env python3
"""Generate the draft night cheat sheet HTML from draft_board.csv."""
import csv, html, os, sys

REPO = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(REPO, "reports/draft_sheet.html")

# Import the real thing rather than reimplementing it - a second copy of the
# VOR maths is how the sheet and the tool drift apart.
sys.path.insert(0, REPO)
from draft_board import build_board, load_players, STARTERS  # noqa: E402

POS = ["FWD", "MID", "DEF", "GK"]
MANAGERS = 8

players = load_players(os.path.join(REPO, "data/2026-27/"))
board, repl = build_board(players, MANAGERS)

rows = []
for p in board:
    rows.append({
        "name": p["name"], "pos": p["pos"], "team": p["team"],
        "pts": p["pts"], "pts24": p["pts24"], "proj": p["proj"],
        "vor": p["vor"], "mins": p["mins"], "tier": p["tier"],
        "cost": p["cost"], "pp90": p["proj_pp90"], "manual": p["manual"],
        "rationale": p["rationale"], "flags": " ".join(p["flags"]),
    })

# NB: counting players above replacement is circular - replacement level IS the
# Nth player, so the count always equals the number drafted. The real signal is
# how far the top of each position sits above its own replacement.
above = {p: sum(1 for r in rows if r["pos"] == p and r["vor"] > 0) for p in POS}
overall = sorted(rows, key=lambda r: -r["vor"])
maxvor = overall[0]["vor"]
fwd_pool = sorted([r for r in rows if r["pos"] == "FWD"], key=lambda r: -r["proj"])
fwd4, fwd6 = fwd_pool[3]["proj"], fwd_pool[5]["proj"]
gk_pool = sorted([r for r in rows if r["pos"] == "GK"], key=lambda r: -r["vor"])
def_t2 = [r for r in rows if r["pos"] == "DEF" and r["tier"] == 2]
# After the top three the board flattens - that plateau is the real shape here.
plateau = overall[3:24]


def esc(s):
    return html.escape(str(s))


def flagchips(r):
    out = []
    for f in r["flags"].split():
        if f in ("INJ", "DOUBT", "SUSP"):
            out.append(f'<span class="chip warn">{f}</span>')
        elif f == "UPSIDE":
            out.append('<span class="chip up">UPSIDE</span>')
        elif f == "NEW":
            out.append('<span class="chip new">NEW</span>')
        elif f == "RETURN":
            out.append('<span class="chip ret">RETURN</span>')
        elif f == "MANUAL":
            out.append('<span class="chip man">EST</span>')
        elif f.endswith("pt"):
            out[-1] = out[-1].replace("RETURN</span>", f"RETURN {f}</span>")
    return "".join(out)


def row_html(rank, r, show_rank=True):
    w = max(2, round(100 * r["vor"] / maxvor)) if r["vor"] > 0 else 0
    rk = f'<td class="rk">{rank}</td>' if show_rank else ""
    return f"""<tr data-id="{esc(r['name'])}-{esc(r['team'])}" class="p-{r['pos']}">
{rk}<td class="nm"><span class="who">{esc(r['name'])}</span><span class="fl">{flagchips(r)}</span></td>
<td><span class="pos p-{r['pos']}">{r['pos']}</span></td>
<td class="tm">{esc(r['team'])}</td>
<td class="num">{r['proj']}</td>
<td class="num vor"><span class="bar" style="width:{w}%"></span><span class="vnum">{r['vor']:+d}</span></td>
<td class="num dim">{r['pts'] or '&mdash;'}<span class="sep">/</span>{r['pts24'] or '&mdash;'}</td>
<td class="num dim">{r['tier'] or '&mdash;'}</td>
<td class="num dim">{r['pp90'] or '&mdash;'}</td>
</tr>"""


board = "\n".join(row_html(i, r) for i, r in enumerate(overall[:44], 1))

panels = []
for p in POS:
    pool = [r for r in rows if r["pos"] == p and r["vor"] > 0]
    pool.sort(key=lambda r: -r["vor"])
    body, last = [], None
    for r in pool[:20]:
        if r["tier"] != last:
            n = sum(1 for x in pool if x["tier"] == r["tier"])
            body.append(f'<tr class="tierrow"><td colspan="8">Tier {r["tier"]} '
                        f'<span class="tn">{n} player{"s" if n != 1 else ""}</span></td></tr>')
            last = r["tier"]
        body.append(row_html(None, r, show_rank=False))
    panels.append(f"""<section class="panel">
<header class="ph p-{p}"><h3>{p}</h3>
<p>{above[p]} above replacement &middot; replacement {repl[p]}pt</p></header>
<div class="scroll"><table class="tbl">
<thead><tr><th>Player</th><th></th><th>Team</th><th class="num">Proj</th><th class="num">VOR</th><th class="num">25-26/24-25</th><th class="num">T</th><th class="num">pp90</th></tr></thead>
<tbody>{''.join(body)}</tbody></table></div></section>""")

ret = sorted([r for r in rows if "RETURN" in r["flags"]],
             key=lambda r: -r["cost"])[:10]
newcomers = sorted([r for r in rows if r["manual"]], key=lambda r: -r["proj"])


def newcomer_rows():
    out = []
    for r in newcomers:
        out.append(f'''<tr data-id="{esc(r['name'])}-{esc(r['team'])}" class="p-{r['pos']} est">
<td class="nm"><span class="who">{esc(r['name'])}</span>{flagchips(r)}</td>
<td><span class="pos p-{r['pos']}">{r['pos']}</span></td><td class="tm">{esc(r['team'])}</td>
<td class="num">{r['proj']}</td><td class="num">{r['vor']:+d}</td>
<td class="why">{esc(r['rationale'])}</td></tr>''')
    return "".join(out)


def watch_rows(items):
    out = []
    for r in items:
        prior = ""
        parts = r["flags"].split()
        for i, f in enumerate(parts):
            if f == "RETURN" and i + 1 < len(parts):
                prior = parts[i + 1]
        out.append(f"""<tr data-id="{esc(r['name'])}-{esc(r['team'])}" class="p-{r['pos']}"><td class="nm"><span class="who">{esc(r['name'])}</span></td>
<td><span class="pos p-{r['pos']}">{r['pos']}</span></td><td class="tm">{esc(r['team'])}</td>
<td class="num dim">{r['cost']:.1f}m</td><td class="num">{prior or '&mdash;'}</td></tr>""")
    return "".join(out)


PAGE = f"""<title>Draft Night Board</title>
<style>
:root {{
  --ground:#F3F6F4; --surface:#FFFFFF; --ink:#0F1714; --muted:#5F726B; --line:#DEE5E1;
  --gk:#B47A10; --def:#0F7A72; --mid:#5B4CC4; --fwd:#BC3C33;
  --gk-b:#B47A1022; --def-b:#0F7A7222; --mid-b:#5B4CC422; --fwd-b:#BC3C3322;
  --warn:#B4571C; --warn-bg:#B4571C1A; --up:#0F7A72; --up-bg:#0F7A721A;
  --shadow:0 1px 2px rgba(15,23,20,.06),0 8px 24px rgba(15,23,20,.05);
}}
@media (prefers-color-scheme: dark) {{
  :root:not([data-theme="light"]) {{
    --ground:#0C120F; --surface:#141D18; --ink:#E3EAE5; --muted:#8A9C94; --line:#24302A;
    --gk:#E0A93F; --def:#35B3A8; --mid:#9385EE; --fwd:#EC6A5E;
    --gk-b:#E0A93F1F; --def-b:#35B3A81F; --mid-b:#9385EE1F; --fwd-b:#EC6A5E1F;
    --warn:#E09A4B; --warn-bg:#E09A4B1F; --up:#35B3A8; --up-bg:#35B3A81F;
    --shadow:0 1px 2px rgba(0,0,0,.4),0 8px 24px rgba(0,0,0,.3);
  }}
}}
:root[data-theme="dark"] {{
  --ground:#0C120F; --surface:#141D18; --ink:#E3EAE5; --muted:#8A9C94; --line:#24302A;
  --gk:#E0A93F; --def:#35B3A8; --mid:#9385EE; --fwd:#EC6A5E;
  --gk-b:#E0A93F1F; --def-b:#35B3A81F; --mid-b:#9385EE1F; --fwd-b:#EC6A5E1F;
  --warn:#E09A4B; --warn-bg:#E09A4B1F; --up:#35B3A8; --up-bg:#35B3A81F;
  --shadow:0 1px 2px rgba(0,0,0,.4),0 8px 24px rgba(0,0,0,.3);
}}
* {{ box-sizing:border-box; }}
body {{
  margin:0; background:var(--ground); color:var(--ink);
  font-family:system-ui,-apple-system,"Segoe UI",sans-serif;
  font-size:15px; line-height:1.5; padding:32px 20px 80px;
}}
.wrap {{ max-width:1180px; margin:0 auto; display:flex; flex-direction:column; gap:34px; }}
h1 {{ font-size:clamp(28px,4.4vw,44px); line-height:1.02; letter-spacing:-.03em;
     margin:0; font-weight:800; text-wrap:balance; }}
h1 em {{ font-style:normal; color:var(--fwd); }}
.sub {{ color:var(--muted); margin:8px 0 0; max-width:62ch; }}
.meta {{ display:flex; flex-wrap:wrap; gap:8px; margin-top:16px; }}
.meta span {{ font-size:11px; letter-spacing:.09em; text-transform:uppercase;
  font-weight:650; color:var(--muted); border:1px solid var(--line);
  border-radius:999px; padding:5px 11px; background:var(--surface); }}
.cards {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(228px,1fr)); gap:14px; }}
.card {{ background:var(--surface); border:1px solid var(--line); border-radius:12px;
  padding:18px; box-shadow:var(--shadow); display:flex; flex-direction:column; gap:6px; }}
.card .k {{ font-size:11px; letter-spacing:.09em; text-transform:uppercase;
  color:var(--muted); font-weight:650; }}
.card .v {{ font-size:32px; font-weight:800; letter-spacing:-.03em;
  font-variant-numeric:tabular-nums; line-height:1; }}
.card .d {{ font-size:13px; color:var(--muted); }}
.panel {{ background:var(--surface); border:1px solid var(--line); border-radius:12px;
  overflow:hidden; box-shadow:var(--shadow); }}
.ph {{ padding:14px 18px; border-bottom:1px solid var(--line);
  display:flex; align-items:baseline; gap:12px; flex-wrap:wrap; }}
.ph h3 {{ margin:0; font-size:15px; letter-spacing:.06em; font-weight:800; }}
.ph p {{ margin:0; font-size:12.5px; color:var(--muted); }}
.ph.p-GK  {{ background:var(--gk-b);  }} .ph.p-GK h3  {{ color:var(--gk); }}
.ph.p-DEF {{ background:var(--def-b); }} .ph.p-DEF h3 {{ color:var(--def); }}
.ph.p-MID {{ background:var(--mid-b); }} .ph.p-MID h3 {{ color:var(--mid); }}
.ph.p-FWD {{ background:var(--fwd-b); }} .ph.p-FWD h3 {{ color:var(--fwd); }}
.scroll {{ overflow-x:auto; }}
.tbl {{ width:100%; border-collapse:collapse; font-size:13.5px; }}
.tbl th {{ text-align:left; font-size:10.5px; letter-spacing:.09em; text-transform:uppercase;
  color:var(--muted); font-weight:650; padding:9px 10px; border-bottom:1px solid var(--line);
  position:sticky; top:0; background:var(--surface); }}
.tbl td {{ padding:7px 10px; border-bottom:1px solid var(--line); vertical-align:middle; }}
.tbl tbody tr {{ cursor:pointer; }}
.tbl tbody tr:hover {{ background:var(--ground); }}
.num {{ text-align:right; font-variant-numeric:tabular-nums;
  font-family:ui-monospace,"SF Mono",Menlo,monospace; white-space:nowrap; }}
.rk {{ width:38px; color:var(--muted); font-variant-numeric:tabular-nums;
  font-family:ui-monospace,"SF Mono",Menlo,monospace; font-size:12px; }}
.nm {{ min-width:180px; }}
.who {{ font-weight:640; }}
.fl {{ margin-left:7px; display:inline-flex; gap:4px; flex-wrap:wrap; }}
.tm {{ color:var(--muted); font-size:12px; font-weight:600; letter-spacing:.04em; }}
.dim {{ color:var(--muted); }}
.pos {{ font-size:10px; font-weight:750; letter-spacing:.07em; padding:2px 6px;
  border-radius:4px; }}
.pos.p-GK  {{ color:var(--gk);  background:var(--gk-b); }}
.pos.p-DEF {{ color:var(--def); background:var(--def-b); }}
.pos.p-MID {{ color:var(--mid); background:var(--mid-b); }}
.pos.p-FWD {{ color:var(--fwd); background:var(--fwd-b); }}
.vor {{ position:relative; min-width:78px; }}
.bar {{ position:absolute; left:6px; top:50%; transform:translateY(-50%); height:16px;
  border-radius:3px; opacity:.2; }}
tr.p-GK  .bar {{ background:var(--gk); }}  tr.p-DEF .bar {{ background:var(--def); }}
tr.p-MID .bar {{ background:var(--mid); }} tr.p-FWD .bar {{ background:var(--fwd); }}
.vnum {{ position:relative; font-weight:680; }}
.chip {{ font-size:9.5px; font-weight:700; letter-spacing:.05em; padding:1px 5px;
  border-radius:3px; white-space:nowrap; }}
.chip.warn {{ color:var(--warn); background:var(--warn-bg); }}
.chip.up {{ color:var(--up); background:var(--up-bg); }}
.chip.new {{ color:var(--muted); background:var(--line); }}
.chip.ret {{ color:var(--mid); background:var(--mid-b); }}
.chip.man {{ color:var(--warn); background:var(--warn-bg); border:1px dashed var(--warn); }}
.sep {{ opacity:.4; padding:0 1px; }}
.est td {{ border-bottom:1px dashed var(--line); }}
.why {{ font-size:12px; color:var(--muted); line-height:1.4; }}
.tierrow td {{ background:var(--ground); font-size:10.5px; letter-spacing:.09em;
  text-transform:uppercase; font-weight:700; color:var(--muted); padding:6px 10px; }}
.tn {{ font-weight:500; text-transform:none; letter-spacing:0; }}
tr.gone {{ opacity:.32; }}
tr.gone .who {{ text-decoration:line-through; }}
.grid2 {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(330px,1fr)); gap:14px; }}
.note {{ background:var(--surface); border:1px solid var(--line); border-left:3px solid var(--fwd);
  border-radius:10px; padding:18px 20px; }}
.note h3 {{ margin:0 0 10px; font-size:14px; letter-spacing:.02em; }}
.note ul {{ margin:0; padding-left:18px; display:flex; flex-direction:column; gap:8px;
  font-size:14px; color:var(--ink); }}
.note strong {{ font-weight:700; }}
.legend {{ display:flex; flex-wrap:wrap; gap:14px; font-size:12.5px; color:var(--muted); }}
.legend b {{ color:var(--ink); font-weight:650; }}
footer {{ color:var(--muted); font-size:12.5px; border-top:1px solid var(--line);
  padding-top:16px; }}
@media (max-width:640px) {{ body {{ padding:20px 12px 60px; }} .nm {{ min-width:140px; }} }}
</style>

<div class="wrap">

<header>
  <h1>Three players, then a <em>plateau</em></h1>
  <p class="sub">Value over replacement for an 8-manager draft, projected from 2025-26 and 2024-25 combined.
  Haaland, Bruno and Gabriel sit clear of everyone. Below them {len(plateau)} players separated by
  {plateau[0]['vor'] - plateau[-1]['vor']} points of VOR &mdash; which means after round three, position scarcity
  should drive your picks, not the ranking.</p>
  <div class="meta">
    <span>2026-27</span><span>8 managers &middot; 120 picked</span>
    <span>Squad 2/5/5/3</span><span>{len(rows)} draftable</span><span>Data pulled 17 Aug 2026</span>
  </div>
</header>

<div class="cards">
  <div class="card"><span class="k">Haaland</span><span class="v">+{overall[0]['vor']}</span>
    <span class="d">VOR. Next best is +{overall[1]['vor']}. The only genuinely automatic pick on the board.</span></div>
  <div class="card"><span class="k">Forward replacement</span><span class="v">{repl['FWD']}<span style="font-size:16px;font-weight:600">pt</span></span>
    <span class="d">Against {repl['MID']}pt at midfield. Forwards are where the floor drops out.</span></div>
  <div class="card"><span class="k">Keeper, then nothing</span><span class="v">+{gk_pool[0]['vor']} &rarr; +{gk_pool[1]['vor']}</span>
    <span class="d">Raya, then the whole position flattens. Take him or take one last.</span></div>
  <div class="card"><span class="k">Defenders in tier 2</span><span class="v">{len(def_t2)}</span>
    <span class="d">From +{max(r['vor'] for r in def_t2)} down to +{min(r['vor'] for r in def_t2)}. The deep value pocket &mdash; raid it mid-draft.</span></div>
</div>

<div class="note">
  <h3>How to play it</h3>
  <ul>
    <li><strong>Round 1 picks itself.</strong> Haaland at +{overall[0]['vor']}, then Bruno +{overall[1]['vor']} and Gabriel +{overall[2]['vor']}. If all three are gone, you are into the plateau and should just take the best forward.</li>
    <li><strong>Rounds 2&ndash;4: get two of the top five forwards.</strong> The 4th forward scored {fwd4}, the 6th scored {fwd6}, and the worst starting forward in the league scores {repl['FWD']}. That drop is steeper than anywhere else on the board.</li>
    <li><strong>Never reach for a midfielder.</strong> Replacement is {repl['MID']}pt &mdash; the highest of any position. There is no midfield cliff, so every early round spent there is value burned.</li>
    <li><strong>Defence is the value pocket.</strong> {len(def_t2)} defenders sit in one broad tier. Let them come to you in the middle rounds instead of paying up early.</li>
    <li><strong>Goalkeeper: Raya or last.</strong> He is +{gk_pool[0]['vor']}; the next keeper is +{gk_pool[1]['vor']} and it is flat from there to +{gk_pool[7]['vor']}. There is no middle ground worth a pick.</li>
    <li><strong>The projection already rescues the injured.</strong> Adding 2024-25 lifted Isak from 268th to inside the top 120 and put Palmer back in the top 60. What it cannot fix is a player whose role changed, so trust last season over the blend when someone has clearly just won a starting job.</li>
    <li><strong>EST players are guesses, not projections.</strong> Anyone marked EST has never played in this league. Only two of them are worth a pick at all &mdash; treat the rest as waiver-wire names you are aware of, not draft targets.</li>
  </ul>
</div>

<section class="panel">
  <header class="ph"><h3>OVERALL BOARD &mdash; TOP 44 BY VOR</h3>
  <p>Click any row to strike a player off. Saved in this browser.</p></header>
  <div class="scroll"><table class="tbl">
  <thead><tr><th>#</th><th>Player</th><th></th><th>Team</th><th class="num">Proj</th><th class="num">VOR</th><th class="num">25-26/24-25</th><th class="num">Tier</th><th class="num">pp90</th></tr></thead>
  <tbody>{board}</tbody></table></div>
</section>

<div class="grid2">{''.join(panels)}</div>

<div class="grid2">
  <section class="panel">
    <header class="ph p-MID"><h3>RETURNING &mdash; NO 25-26 MINUTES</h3>
    <p>Real Premier League pedigree, invisible if you rank on last season alone.</p></header>
    <div class="scroll"><table class="tbl">
    <thead><tr><th>Player</th><th></th><th>Team</th><th class="num">Price</th><th class="num">Best PL yr</th></tr></thead>
    <tbody>{watch_rows(ret)}</tbody></table></div>
  </section>
  <section class="panel">
    <header class="ph"><h3>NEW TO THE LEAGUE &mdash; ESTIMATES</h3>
    <p>No Premier League history, so these are scouting estimates rather than projections.</p></header>
    <div class="scroll"><table class="tbl">
    <thead><tr><th>Player</th><th></th><th>Team</th><th class="num">Est</th><th class="num">VOR</th><th>Why</th></tr></thead>
    <tbody>{newcomer_rows()}</tbody></table></div>
  </section>
</div>

<div class="legend">
  <span><b>VOR</b> points above the best player still free at that position</span>
  <span><b>pp90</b> points per 90 minutes</span>
  <span><b>UPSIDE</b> strong rate, few minutes</span>
  <span><b>RETURN</b> played in the PL before, not last season</span>
  <span><b>EST</b> hand estimate &mdash; no PL history to model</span>
  <span><b>INJ / DOUBT</b> current FPL status</span>
</div>

<footer>
  Projection blends 2025-26 and 2024-25, weighting each season by the minutes behind it and
  rescaling 2024-25 onto the current scoring system (defensive contribution points arrived in
  2025-26 and inflated defender scoring by 27%). Playing time leans on last season.
  Replacement level assumes 8 managers filling 2 GK / 5 DEF / 5 MID / 3 FWD.
  Players who have left the league are excluded.
</footer>
</div>

<script>
(function () {{
  var KEY = 'fpl-draft-2026-27-gone';
  var gone;
  try {{ gone = new Set(JSON.parse(localStorage.getItem(KEY) || '[]')); }}
  catch (e) {{ gone = new Set(); }}

  function paint() {{
    document.querySelectorAll('tr[data-id]').forEach(function (tr) {{
      tr.classList.toggle('gone', gone.has(tr.dataset.id));
    }});
  }}
  document.addEventListener('click', function (e) {{
    var tr = e.target.closest('tr[data-id]');
    if (!tr) return;
    var id = tr.dataset.id;
    gone.has(id) ? gone.delete(id) : gone.add(id);
    try {{ localStorage.setItem(KEY, JSON.stringify([].slice.call(gone))); }} catch (e) {{}}
    paint();
  }});
  paint();
}})();
</script>
"""

open(OUT, "w").write(PAGE)
print("wrote", OUT, len(PAGE), "bytes")
print("above replacement:", above)
print("replacement:", repl)
