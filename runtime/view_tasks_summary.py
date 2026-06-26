"""
Generate exports/view/tasks.html — tasks recap by month.

One section per month, one row per project showing days worked.
"""

import locale
try:
    locale.setlocale(locale.LC_ALL, 'fr_FR')
except locale.Error:
    locale.setlocale(locale.LC_ALL, '')

import os
from datetime import datetime
from collections import defaultdict

import configs
from packages.database.database import Database

# ─── load ─────────────────────────────────────────────────────────────────────

db = Database.init_billing()

# ─── aggregate tasks by month → project ───────────────────────────────────────
# structure: { "YYYY-MM": { project_uid: { name, days } } }

by_month = defaultdict(lambda: defaultdict(lambda: {"name": "", "days": 0.0, "zero": 0}))

for p in db.projects:
    for t in p.tasks:
        month = t.date.strftime("%Y-%m")
        by_month[month][p.uid]["name"] = p.name
        if t.getTimeSpent() == 0:
            by_month[month][p.uid]["zero"] += 1
        else:
            by_month[month][p.uid]["days"] += t.getTimeSpent()

# all project uids seen across all months (for consistent ordering)
all_project_uids = []
for month_data in by_month.values():
    for uid in month_data:
        if uid not in all_project_uids:
            all_project_uids.append(uid)

# project name lookup
project_names = {p.uid: p.name for p in db.projects}

# ─── helpers ──────────────────────────────────────────────────────────────────

def fmt_days(v):
    return f"{v:g}" if v > 0 else "—"

def card(label, value):
    return f'<div class="card"><div class="card-label">{label}</div><div class="card-value">{value}</div></div>'

# ─── build month sections ─────────────────────────────────────────────────────

total_days_all = 0.0

# group by year → month number
by_year = defaultdict(dict)
for month, projects in by_month.items():
    dt = datetime.strptime(month, "%Y-%m")
    by_year[dt.year][dt.month] = projects
    total_days_all += sum(d["days"] for d in projects.values())

MONTH_ABBR = ["Jan","Fév","Mar","Avr","Mai","Jun","Jul","Aoû","Sep","Oct","Nov","Déc"]

month_sections = ""

current_year = datetime.now().year

for year in sorted(by_year.keys()):  # oldest → newest = top → bottom
    months = by_year[year]
    year_days = sum(sum(d["days"] for d in m.values()) for m in months.values())

    yid = f"year-{year}"
    folded = "" if year == current_year else " collapsed"
    arrow = "▾" if year == current_year else "▸"
    month_sections += f'<div class="year-header{folded}" onclick="toggleYear(\'{yid}\')" data-yid="{yid}"><span class="year-arrow">{arrow}</span><span class="year-label">{year}</span><span class="year-total">{fmt_days(year_days)} j</span></div>'
    month_sections += f'<div class="cal-grid{folded}" id="{yid}">'

    for mo in range(1, 13):
        projects = months.get(mo)
        label = MONTH_ABBR[mo - 1]

        if not projects:
            month_sections += f'<div class="month-block empty-month"><div class="month-header"><span class="month-name">{label}</span></div></div>'
            continue

        month_total = sum(d["days"] for d in projects.values())
        rows = ""
        for uid, d in sorted(projects.items(), key=lambda x: -x[1]["days"]):
            zero_badge = f' <span class="zero-badge">{d["zero"]}×0</span>' if d["zero"] else ""
            rows += f"""<tr>
              <td>{d['name']}{zero_badge}</td>
              <td class="num">{fmt_days(d['days'])}</td>
            </tr>"""
        rows += f"""<tr class="total-row">
          <td>Total</td>
          <td class="num">{fmt_days(month_total)}</td>
        </tr>"""

        month_sections += f"""
        <div class="month-block">
          <div class="month-header">
            <span class="month-name">{label}</span>
            <span class="month-total">{fmt_days(month_total)} j</span>
          </div>
          <table>
            <thead><tr><th>Projet</th><th>J</th></tr></thead>
            <tbody>{rows}</tbody>
          </table>
        </div>"""

    month_sections += '</div>'

# ─── summary cards ────────────────────────────────────────────────────────────

total_months = len(by_month)
avg_per_month = total_days_all / total_months if total_months else 0

summary = f"""<div class="cards">
  {card("Jours total", f"{total_days_all:g}")}
  {card("Mois", str(total_months))}
  {card("Moyenne / mois", f"{avg_per_month:.1f}")}
</div>"""

# ─── assemble ─────────────────────────────────────────────────────────────────

generated_at = datetime.now().strftime("%Y-%m-%d %H:%M")

html = f"""<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8"/>
<title>Tasks view</title>
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ font-family: system-ui, sans-serif; font-size: 14px; background: #f5f5f5; color: #222; padding: 32px; }}
  h1 {{ font-size: 20px; font-weight: 700; margin-bottom: 4px; }}
  .meta {{ color: #888; font-size: 12px; margin-bottom: 24px; }}

  .cards {{ display: flex; gap: 12px; flex-wrap: wrap; margin-bottom: 32px; }}
  .card {{ background: #fff; border-radius: 8px; padding: 14px 20px; min-width: 130px;
            box-shadow: 0 1px 3px rgba(0,0,0,.07); }}
  .card-label {{ font-size: 10px; color: #aaa; text-transform: uppercase; letter-spacing: .05em; }}
  .card-value {{ font-size: 20px; font-weight: 700; margin-top: 4px; }}

  .cal-grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(180px, 1fr)); gap: 8px; margin-bottom: 8px; }}

  .year-header {{ display: flex; align-items: center; gap: 12px;
                  margin: 32px 0 12px; padding-bottom: 8px;
                  border-bottom: 2px solid #ddd;
                  cursor: pointer; user-select: none; }}
  .year-header:hover .year-label {{ color: #000; }}
  .year-label {{ font-size: 18px; font-weight: 700; color: #333; }}
  .year-total {{ font-size: 13px; color: #999; }}
  .year-arrow {{ display: inline-flex; align-items: center; justify-content: center;
                 width: 22px; height: 22px; border-radius: 50%;
                 background: #e0e0e0; color: #444; font-size: 13px;
                 transition: transform .2s, background .15s; flex-shrink: 0; }}
  .year-header:hover .year-arrow {{ background: #ccc; }}
  .year-header.collapsed .year-arrow {{ transform: rotate(-90deg); }}
  .cal-grid.collapsed {{ display: none; }}

  .month-block {{ background: #fff; border-radius: 8px;
                  box-shadow: 0 1px 3px rgba(0,0,0,.07); overflow: hidden; }}
  .empty-month {{ opacity: .3; }}
  .month-header {{ display: flex; justify-content: space-between; align-items: baseline;
                   padding: 12px 16px; background: #f7f7f7; border-bottom: 1px solid #eee; }}
  .month-name {{ font-weight: 600; font-size: 14px; text-transform: capitalize; }}
  .month-total {{ font-size: 13px; color: #888; }}

  table {{ width: 100%; border-collapse: collapse; }}
  th {{ text-align: left; padding: 6px 16px; font-size: 10px; text-transform: uppercase;
        letter-spacing: .05em; color: #aaa; background: #fafafa; }}
  td {{ padding: 6px 16px; border-top: 1px solid #f0f0f0; }}
  tr:hover td {{ background: #fafafa; }}
  .num {{ text-align: right; font-variant-numeric: tabular-nums; font-weight: 500; }}
  .total-row td {{ font-weight: 600; border-top: 2px solid #eee; color: #555; }}
  .zero-badge {{ display: inline-block; font-size: 10px; font-weight: 600;
                 background: #fdecea; color: #c62828; border-radius: 4px;
                 padding: 1px 5px; margin-left: 5px; }}
</style>
</head>
<body>

<h1>Tasks</h1>
<div class="meta">Généré le {generated_at}</div>

{summary}

{month_sections}

<script>
function toggleYear(yid) {{
  const grid   = document.getElementById(yid);
  const header = document.querySelector('[data-yid="' + yid + '"]');
  grid.classList.toggle('collapsed');
  header.classList.toggle('collapsed');
}}
</script>
</body>
</html>"""

# ─── write ────────────────────────────────────────────────────────────────────

out_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "exports", "view"))
os.makedirs(out_dir, exist_ok=True)
out_path = os.path.join(out_dir, "tasks.html")

with open(out_path, "w", encoding="utf-8") as f:
    f.write(html)

print(f"\n── tasks ──")
print(f"mois chargés : {len(by_month)}")
print(f"jours total  : {total_days_all:g}")
print(f"view @ {out_path}")

if hasattr(os, "startfile"):
    os.startfile(os.path.normpath(out_path))

if configs.pause_on_exit: input("\nEntrée pour fermer...")
