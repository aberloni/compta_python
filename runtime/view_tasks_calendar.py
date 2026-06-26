"""
Generate exports/view/tasks_calendar.html — monthly calendar view.

One tab per month. Each day cell shows project entries with time spent.
"""

import locale
import sys
import traceback

def _excepthook(etype, value, tb):
    traceback.print_exception(etype, value, tb)
    if configs.pause_on_exit: input("\nEntrée pour fermer...")
sys.excepthook = _excepthook

try:
    locale.setlocale(locale.LC_ALL, 'fr_FR')
except locale.Error:
    locale.setlocale(locale.LC_ALL, '')

import os
import calendar
from datetime import datetime, date
from collections import defaultdict

import configs
from packages.database.database import Database

# ─── load ─────────────────────────────────────────────────────────────────────

db = Database.init_billing()

# ─── assign a stable color per project ────────────────────────────────────────

PALETTE = [
    "#ffadad", "#ffd6a5", "#fdffb6", "#caffbf", "#9bf6ff",
    "#a0c4ff", "#bdb2ff", "#ffc6ff", "#fffffc", "#b5ead7",
    "#f9c6c9", "#fce38a", "#95e1d3", "#c9b1ff", "#ffd3b6",
    "#dcedc1", "#a8e6cf", "#ffd3e0", "#d4f1f4", "#e8d5f5",
]

# stable assignment: sort projects by uid for determinism, assign palette index
project_colors = {}
for i, p in enumerate(sorted(db.projects, key=lambda x: x.uid)):
    project_colors[p.uid] = PALETTE[i % len(PALETTE)]

project_names = {p.uid: p.name for p in db.projects}

# ─── aggregate tasks by date ──────────────────────────────────────────────────
# { date: [ {uid, name, days} ] }

by_date = defaultdict(list)

for p in db.projects:
    for t in p.tasks:
        by_date[t.date.date() if hasattr(t.date, 'date') else t.date].append({
            "uid":   p.uid,
            "name":  p.name,
            "days":  t.getTimeSpent(),
            "color": project_colors[p.uid],
        })

# sort entries within each day by days desc
for d in by_date:
    by_date[d].sort(key=lambda x: -x["days"])

# ─── months with data ─────────────────────────────────────────────────────────

months_with_data = sorted({d.strftime("%Y-%m") for d in by_date.keys()}, reverse=True)
print(f"dates chargées : {len(by_date)}  —  mois : {months_with_data[:3]}...")

# ─── helpers ──────────────────────────────────────────────────────────────────

DAY_HEADERS = ["Lun", "Mar", "Mer", "Jeu", "Ven", "Sam", "Dim"]

def fmt_days(v):
    if v == 0:   return "0"
    if v == 1.0: return "1 j"
    return f"{v:g} j"

def render_month(ym):
    year, month = int(ym[:4]), int(ym[5:])
    _, num_days = calendar.monthrange(year, month)
    first_weekday = date(year, month, 1).weekday()  # 0=Mon

    total_by_project = defaultdict(float)
    cells = []

    # empty cells before first day
    for _ in range(first_weekday):
        cells.append('<div class="day-cell empty"></div>')

    for day in range(1, num_days + 1):
        d = date(year, month, day)
        weekday  = d.weekday()
        entries  = by_date.get(d, [])

        day_total = sum(e["days"] for e in entries)
        for e in entries:
            total_by_project[e["uid"]] += e["days"]

        weekend_cls = " weekend" if weekday >= 5 else ""
        today_cls   = " today"   if d == date.today() else ""

        bar_html = ""
        if entries and day_total > 0:
            # each segment proportional to its share of the day total
            for e in entries:
                if e["days"] <= 0:
                    continue
                pct   = e["days"] / day_total * 100
                title = f'{e["name"]} — {fmt_days(e["days"])}'
                bar_html += f'<div class="bar-seg" style="height:{pct:.1f}%;background:{e["color"]}" title="{title}"><span class="bar-label">{e["name"]}</span></div>'
        elif entries:
            # only zero-day entries — split equally
            pct = 100 / len(entries)
            for e in entries:
                name  = e["name"]
                bar_html += f'<div class="bar-seg zero-seg" style="height:{pct:.1f}%" title="{name} — 0 j"><span class="bar-label">{name}</span></div>'

        total_label = f'<div class="day-total">{fmt_days(day_total)}</div>' if day_total > 0 else ""

        cells.append(f"""<div class="day-cell{weekend_cls}{today_cls}">
          <div class="day-num">{day}</div>
          <div class="bar-wrap">{bar_html}</div>
          {total_label}
        </div>""")

    # pad last row
    remainder = len(cells) % 7
    if remainder:
        for _ in range(7 - remainder):
            cells.append('<div class="day-cell empty"></div>')

    grid = "\n".join(cells)

    # legend
    legend = ""
    for uid, total in sorted(total_by_project.items(), key=lambda x: -x[1]):
        color = project_colors.get(uid, "#ccc")
        name  = project_names.get(uid, uid)
        legend += f'<div class="legend-item"><span class="legend-dot" style="background:{color}"></span>{name}<span class="legend-days">{fmt_days(total)}</span></div>'

    month_total = sum(total_by_project.values())
    legend += f'<div class="legend-item total-legend"><span class="legend-dot"></span>Total<span class="legend-days">{fmt_days(month_total)}</span></div>'

    headers = "".join(f'<div class="day-header">{h}</div>' for h in DAY_HEADERS)

    state_legend = """
    <div class="state-legend">
      <span class="state-item"><span class="state-swatch" style="background:#f0f0f0"></span>Aucune tâche</span>
      <span class="state-item"><span class="state-swatch" style="background:#fafafa;border:1px solid #eee"></span>Weekend</span>
      <span class="state-item"><span class="state-swatch" style="background:#fffbe6"></span>Aujourd'hui</span>
      <span class="state-item"><span class="state-swatch" style="background:#fdecea"></span>Jour × 0</span>
    </div>"""

    return f"""
    <div class="legend">{legend}</div>
    {state_legend}
    <div class="cal-grid">
      <div class="day-headers">{headers}</div>
      <div class="days">{grid}</div>
    </div>"""

# ─── build tabs ───────────────────────────────────────────────────────────────

tabs_nav = ""
tabs_content = ""
current_ym = datetime.now().strftime("%Y-%m")

for i, ym in enumerate(months_with_data):
    tid    = f"tab-{ym}"
    active = "active" if ym == current_ym or (i == 0 and current_ym not in months_with_data) else ""
    label  = datetime.strptime(ym, "%Y-%m").strftime("%b %Y").capitalize()
    tabs_nav     += f'<button class="tab-btn {active}" onclick="showTab(\'{tid}\')" id="btn-{tid}">{label}</button>'
    tabs_content += f'<div class="tab-panel {active}" id="{tid}">{render_month(ym)}</div>'

# ─── assemble ─────────────────────────────────────────────────────────────────

generated_at = datetime.now().strftime("%Y-%m-%d %H:%M")

html = f"""<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8"/>
<title>Tasks calendrier</title>
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ font-family: system-ui, sans-serif; font-size: 13px; background: #f5f5f5; color: #222; padding: 24px 32px; }}
  h1 {{ font-size: 20px; font-weight: 700; margin-bottom: 4px; }}
  .meta {{ color: #888; font-size: 12px; margin-bottom: 20px; }}

  /* tabs */
  .tabs-nav {{ display: flex; flex-wrap: wrap; gap: 6px; margin-bottom: 20px; }}
  .tab-btn {{ padding: 6px 14px; border: 1px solid #ddd; border-radius: 20px;
              background: #fff; cursor: pointer; font-size: 12px; font-weight: 500;
              color: #555; transition: background .15s; }}
  .tab-btn:hover {{ background: #f0f0f0; }}
  .tab-btn.active {{ background: #222; color: #fff; border-color: #222; }}
  .tab-panel {{ display: none; }}
  .tab-panel.active {{ display: block; }}

  /* legend */
  .legend {{ display: flex; flex-wrap: wrap; gap: 10px 20px; margin-bottom: 16px; }}
  .legend-item {{ display: flex; align-items: center; gap: 6px; font-size: 12px; color: #555; }}
  .legend-dot {{ width: 10px; height: 10px; border-radius: 50%; flex-shrink: 0; }}
  .legend-days {{ margin-left: 6px; font-weight: 600; color: #333; }}
  .total-legend {{ font-weight: 700; color: #222; }}

  /* calendar */
  .cal-grid {{ background: #fff; border-radius: 10px; box-shadow: 0 1px 4px rgba(0,0,0,.08); overflow: hidden; }}
  .day-headers {{ display: grid; grid-template-columns: repeat(7, 1fr);
                  background: #f7f7f7; border-bottom: 1px solid #eee; }}
  .day-header {{ padding: 8px; text-align: center; font-size: 11px; font-weight: 600;
                 text-transform: uppercase; letter-spacing: .05em; color: #aaa; }}
  .days {{ display: grid; grid-template-columns: repeat(7, 1fr); }}
  .day-cell {{ height: 90px; padding: 6px; border-right: 1px solid #f0f0f0;
               border-bottom: 1px solid #f0f0f0; display: flex; flex-direction: column; }}
  .day-cell.empty {{ background: #fafafa; }}
  .day-cell.weekend {{ background: #fafafa; }}
  .day-cell.today {{ background: #fffbe6; }}
  .day-cell:nth-child(7n) {{ border-right: none; }}
  .day-num {{ font-size: 11px; font-weight: 700; color: #bbb; margin-bottom: 4px; flex-shrink: 0; }}
  .today .day-num {{ color: #e65100; }}
  .weekend .day-num {{ color: #ddd; }}

  /* stacked bar */
  .bar-wrap {{ flex: 1; border-radius: 4px; overflow: hidden; display: flex;
               flex-direction: column; background: #f0f0f0; min-height: 0; }}
  .bar-seg {{ width: 100%; transition: opacity .15s; position: relative;
              display: flex; align-items: center; overflow: hidden; }}
  .bar-seg:hover {{ opacity: .75; cursor: default; }}
  .zero-seg {{ background: #fdecea !important; }}
  .bar-label {{ font-size: 9px; font-weight: 600; color: rgba(0,0,0,.6);
                padding: 0 4px; white-space: nowrap; overflow: hidden;
                text-overflow: ellipsis; pointer-events: none; }}

  .day-total {{ font-size: 9px; font-weight: 700; color: #bbb; text-align: right;
                margin-top: 3px; flex-shrink: 0; }}

  /* state legend */
  .state-legend {{ display: flex; gap: 16px; flex-wrap: wrap; margin-bottom: 12px; }}
  .state-item {{ display: flex; align-items: center; gap: 6px; font-size: 11px; color: #888; }}
  .state-swatch {{ display: inline-block; width: 14px; height: 14px; border-radius: 3px;
                   border: 1px solid #e0e0e0; flex-shrink: 0; }}
</style>
</head>
<body>

<h1>Tasks — calendrier</h1>
<div class="meta">Généré le {generated_at}</div>

<div class="tabs-nav">{tabs_nav}</div>

{tabs_content}

<script>
function showTab(id) {{
  document.querySelectorAll('.tab-panel').forEach(p => p.classList.remove('active'));
  document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
  document.getElementById(id).classList.add('active');
  document.getElementById('btn-' + id).classList.add('active');
}}
</script>
</body>
</html>"""

# ─── write ────────────────────────────────────────────────────────────────────

out_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "exports", "view"))
os.makedirs(out_dir, exist_ok=True)
out_path = os.path.join(out_dir, "tasks_calendar.html")

with open(out_path, "w", encoding="utf-8") as f:
    f.write(html)

print(f"\n── tasks_calendar ──")
print(f"mois : {len(months_with_data)}")
print(f"view @ {out_path}")

if hasattr(os, "startfile"):
    os.startfile(os.path.normpath(out_path))

if configs.pause_on_exit: input("\nEntrée pour fermer...")
