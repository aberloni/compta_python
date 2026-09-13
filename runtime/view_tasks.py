"""
Generate exports/view/tasks.html — tasks recap.

Tabs: "Aucun" (default) shows tasks aggregated by month across all projects.
One tab per project shows that project's own calendar (billed / non-billed /
zero-day tasks), Jan→Dec.
"""

import locale
import sys
import traceback
import os
from datetime import datetime
from collections import defaultdict

import configs

def _excepthook(etype, value, tb):
    traceback.print_exception(etype, value, tb)
    if configs.pause_on_exit and not configs.webview_mode: input("\nEntrée pour fermer...")
sys.excepthook = _excepthook

try:
    locale.setlocale(locale.LC_ALL, 'fr_FR')
except locale.Error:
    locale.setlocale(locale.LC_ALL, '')

from packages.database.database import Database
from modules.layout import render_shell

# ─── load ─────────────────────────────────────────────────────────────────────

db = Database.init_billing()

# ─── helpers ──────────────────────────────────────────────────────────────────

MONTH_ABBR = ["Jan","Fév","Mar","Avr","Mai","Jun","Jul","Aoû","Sep","Oct","Nov","Déc"]

def fmt_days(v):
    return f"{v:g}" if v > 0 else "—"

def card(label, value, sub=""):
    sub_html = f'<div class="card-sub">{sub}</div>' if sub else ""
    return f'<div class="card"><div class="card-label">{label}</div><div class="card-value">{value}</div>{sub_html}</div>'

# ─── "Aucun" tab : tasks aggregated by month across all projects ──────────────

def build_none_tab():
    by_month = defaultdict(lambda: defaultdict(lambda: {"name": "", "days": 0.0, "zero": 0}))

    for p in db.projects:
        for t in p.tasks:
            month = t.date.strftime("%Y-%m")
            by_month[month][p.uid]["name"] = p.name
            if t.getTimeSpent() == 0:
                by_month[month][p.uid]["zero"] += 1
            else:
                by_month[month][p.uid]["days"] += t.getTimeSpent()

    total_days_all = 0.0
    by_year = defaultdict(dict)
    for month, projects_data in by_month.items():
        dt = datetime.strptime(month, "%Y-%m")
        by_year[dt.year][dt.month] = projects_data
        total_days_all += sum(d["days"] for d in projects_data.values())

    month_sections = ""
    current_year = datetime.now().year

    for year in sorted(by_year.keys()):
        months = by_year[year]
        year_days = sum(sum(d["days"] for d in m.values()) for m in months.values())

        yid = f"year-none-{year}"
        folded = "" if year == current_year else " collapsed"
        arrow = "▾" if year == current_year else "▸"
        month_sections += f'<div class="year-header{folded}" onclick="toggleYear(\'{yid}\')" data-yid="{yid}" data-year="{year}"><span class="year-arrow">{arrow}</span><span class="year-label">{year}</span><span class="year-total">{fmt_days(year_days)} j</span></div>'
        month_sections += f'<div class="cal-grid{folded}" id="{yid}">'

        for mo in range(1, 13):
            projects_data = months.get(mo)
            label = MONTH_ABBR[mo - 1]

            if not projects_data:
                month_sections += f'<div class="month-block empty-month"><div class="month-header"><span class="month-name">{label}</span></div></div>'
                continue

            month_total = sum(d["days"] for d in projects_data.values())
            rows = ""
            for uid, d in sorted(projects_data.items(), key=lambda x: -x[1]["days"]):
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

        month_sections += "</div>"

    total_months = len(by_month)
    avg_per_month = total_days_all / total_months if total_months else 0

    summary = f"""<div class="cards">
      {card("Jours total", f"{total_days_all:g}")}
      {card("Mois", str(total_months))}
      {card("Moyenne / mois", f"{avg_per_month:.1f}")}
    </div>"""

    return f"{summary}{month_sections}", total_days_all, total_months, sorted(by_year.keys())

# ─── per-project tabs ──────────────────────────────────────────────────────────

def build_project_tab(p):
    # index billed task ids
    billed_ids = {id(t) for b in p.bills for t in b.tasks}

    # group tasks by YYYY-MM → category (billed / unbilled / zero)
    by_month = defaultdict(lambda: {"billed": [], "unbilled": [], "zero": []})

    for t in p.tasks:
        month = t.date.strftime("%Y-%m")
        days = t.getTimeSpent()
        if days == 0:
            by_month[month]["zero"].append(t)
        elif id(t) in billed_ids:
            by_month[month]["billed"].append(t)
        else:
            by_month[month]["unbilled"].append(t)

    # totals
    total_billed   = sum(sum(t.getTimeSpent() for t in v["billed"])   for v in by_month.values())
    total_unbilled = sum(sum(t.getTimeSpent() for t in v["unbilled"]) for v in by_month.values())
    total_zero     = sum(len(v["zero"]) for v in by_month.values())
    total_days     = total_billed + total_unbilled

    # group by year
    by_year = defaultdict(dict)
    for month, cats in by_month.items():
        dt = datetime.strptime(month, "%Y-%m")
        by_year[dt.year][dt.month] = cats

    # calendar HTML
    cal_html = ""
    for year in sorted(by_year.keys()):
        months = by_year[year]
        year_days = sum(
            sum(t.getTimeSpent() for t in cats["billed"] + cats["unbilled"])
            for cats in months.values()
        )
        current_year = datetime.now().year
        yid = f"year-{p.uid}-{year}"
        folded = "" if year == current_year else " collapsed"
        cal_html += f'<div class="year-header{folded}" onclick="toggleYear(\'{yid}\')" data-yid="{yid}" data-year="{year}"><span class="year-arrow">{"▾" if not folded else "▸"}</span><span class="year-label">{year}</span><span class="year-total">{fmt_days(year_days)} j</span></div>'
        cal_html += f'<div class="cal-grid{folded}" id="{yid}">'

        for mo in range(1, 13):
            label = MONTH_ABBR[mo - 1]
            cats = months.get(mo)

            if not cats:
                cal_html += f'<div class="month-block empty-month"><div class="month-header"><span class="month-name">{label}</span></div></div>'
                continue

            billed_days   = sum(t.getTimeSpent() for t in cats["billed"])
            unbilled_days = sum(t.getTimeSpent() for t in cats["unbilled"])
            month_total   = billed_days + unbilled_days
            rows = ""

            all_tasks = sorted(cats["billed"] + cats["unbilled"] + cats["zero"], key=lambda x: x.date)
            for t in all_tasks:
                days = t.getTimeSpent()
                if days == 0:
                    css = "zero-row"
                    val = "0"
                elif id(t) in billed_ids:
                    css = "billed-row"
                    val = fmt_days(days)
                else:
                    css = "unbilled-row"
                    val = fmt_days(days)
                rows += f'<tr class="{css}"><td>{t.date.strftime("%d")}</td><td class="num">{val}</td></tr>'

            rows += f'<tr class="total-row"><td>Total</td><td class="num">{fmt_days(month_total)}</td></tr>'

            cal_html += f"""
            <div class="month-block">
              <div class="month-header">
                <span class="month-name">{label}</span>
                <span class="month-total">{fmt_days(month_total)} j</span>
              </div>
              <table><tbody>{rows}</tbody></table>
            </div>"""

        cal_html += "</div>"

    cards_html = f"""<div class="cards">
      {card("Total jours", f"{fmt_days(total_days)} j")}
      {card("Facturés", f"{fmt_days(total_billed)} j")}
      {card("Non facturés", f"{fmt_days(total_unbilled)} j")}
      {card("Jours × 0", str(total_zero))}
    </div>"""

    return f"{cards_html}{cal_html}"

# ─── build tabs ───────────────────────────────────────────────────────────────

projects = [p for p in db.projects if p.tasks]
projects.sort(key=lambda p: p.name)

none_content, total_days_all, total_months, all_years = build_none_tab()

tabs_nav = '<button class="tab-btn active" onclick="showTab(\'tab-none\')" id="btn-tab-none">Aucun</button>'
tabs_content = f'<div class="tab-panel active" id="tab-none">{none_content}</div>'

for p in projects:
    tid = f"tab-{p.uid}"
    tabs_nav     += f'<button class="tab-btn" onclick="showTab(\'{tid}\')" id="btn-{tid}">{p.name}</button>'
    tabs_content += f'<div class="tab-panel" id="{tid}">{build_project_tab(p)}</div>'

years_nav = '<button class="tab-btn year-btn active" onclick="selectYear(\'all\')" id="btn-year-all">Toutes années</button>'
for year in sorted(all_years, reverse=True):
    years_nav += f'<button class="tab-btn year-btn" onclick="selectYear(\'{year}\')" id="btn-year-{year}">{year}</button>'

# ─── assemble ─────────────────────────────────────────────────────────────────

generated_at = datetime.now().strftime("%Y-%m-%d %H:%M")

page_style = """
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { font-family: system-ui, sans-serif; font-size: 14px; background: #f5f5f5; color: #222; }
  h1 { font-size: 20px; font-weight: 700; margin-bottom: 4px; }
  .meta { color: #888; font-size: 12px; margin-bottom: 24px; }

  /* tabs */
  .tabs-nav { display: flex; flex-wrap: wrap; gap: 6px; margin-bottom: 24px; }
  .tab-btn { padding: 7px 16px; border: 1px solid #ddd; border-radius: 20px;
              background: #fff; cursor: pointer; font-size: 13px; font-weight: 500;
              color: #555; transition: background .15s, color .15s; }
  .tab-btn:hover { background: #f0f0f0; }
  .tab-btn.active { background: #222; color: #fff; border-color: #222; }
  .tab-panel { display: none; }
  .tab-panel.active { display: block; }

  /* cards */
  .cards { display: flex; gap: 12px; flex-wrap: wrap; margin-bottom: 28px; }
  .card { background: #fff; border-radius: 8px; padding: 14px 20px; min-width: 130px;
            box-shadow: 0 1px 3px rgba(0,0,0,.07); }
  .card-label { font-size: 10px; color: #aaa; text-transform: uppercase; letter-spacing: .05em; }
  .card-value { font-size: 20px; font-weight: 700; margin-top: 4px; }
  .card-sub { font-size: 11px; color: #bbb; margin-top: 2px; }

  /* calendar grid */
  .cal-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(160px, 1fr)); gap: 8px; margin-bottom: 8px; }

  .year-header { display: flex; align-items: center; gap: 12px;
                  margin: 28px 0 12px; padding-bottom: 8px;
                  border-bottom: 2px solid #ddd;
                  cursor: pointer; user-select: none; }
  .year-header:hover .year-label { color: #000; }
  .year-label { font-size: 18px; font-weight: 700; color: #333; }
  .year-total { font-size: 13px; color: #999; }
  .year-arrow { display: inline-flex; align-items: center; justify-content: center;
                 width: 22px; height: 22px; border-radius: 50%;
                 background: #e0e0e0; color: #444; font-size: 13px;
                 transition: transform .2s, background .15s; flex-shrink: 0; }
  .year-header:hover .year-arrow { background: #ccc; }
  .year-header.collapsed .year-arrow { transform: rotate(-90deg); }
  .cal-grid.collapsed { display: none; }

  .month-block { background: #fff; border-radius: 8px;
                  box-shadow: 0 1px 3px rgba(0,0,0,.07); overflow: hidden; }
  .empty-month { opacity: .3; }
  .month-header { display: flex; justify-content: space-between; align-items: baseline;
                   padding: 10px 14px; background: #f7f7f7; border-bottom: 1px solid #eee; }
  .month-name { font-weight: 600; font-size: 13px; }
  .month-total { font-size: 12px; color: #888; }

  table { width: 100%; border-collapse: collapse; }
  th { text-align: left; padding: 6px 14px; font-size: 10px; text-transform: uppercase;
        letter-spacing: .05em; color: #aaa; background: #fafafa; }
  td { padding: 4px 14px; font-size: 12px; border-top: 1px solid #f0f0f0; }
  .num { text-align: left; font-variant-numeric: tabular-nums; font-weight: 500; }
  .total-row td { font-weight: 600; border-top: 2px solid #eee; color: #555; padding-top: 6px; }
  .zero-badge { display: inline-block; font-size: 10px; font-weight: 600;
                 background: #fdecea; color: #c62828; border-radius: 4px;
                 padding: 1px 5px; margin-left: 5px; }

  /* row colours (per-project tabs) */
  .billed-row td { color: #2e7d32; }
  .unbilled-row td { color: #b07a00; }
  .zero-row td { color: #c62828; }
"""

body_content = f"""
<h1>Tâches</h1>
<div class="meta">Généré le {generated_at}</div>

<div class="tabs-nav">{tabs_nav}</div>
<div class="tabs-nav">{years_nav}</div>

{tabs_content}

<script>
let selectedYear = 'all';

function showTab(id) {{
  document.querySelectorAll('.tab-panel').forEach(p => p.classList.remove('active'));
  document.querySelectorAll('.tab-btn:not(.year-btn)').forEach(b => b.classList.remove('active'));
  document.getElementById(id).classList.add('active');
  document.getElementById('btn-' + id).classList.add('active');
  applyYearFilter();
}}
function toggleYear(yid) {{
  const grid   = document.getElementById(yid);
  const header = document.querySelector('[data-yid="' + yid + '"]');
  grid.classList.toggle('collapsed');
  header.classList.toggle('collapsed');
}}
function selectYear(year) {{
  selectedYear = String(year);
  document.querySelectorAll('.year-btn').forEach(b => b.classList.remove('active'));
  document.getElementById('btn-year-' + year).classList.add('active');
  applyYearFilter();
}}
function applyYearFilter() {{
  const activePanel = document.querySelector('.tab-panel.active');
  if (!activePanel) return;
  activePanel.querySelectorAll('.year-header').forEach(h => {{
    h.style.display = (selectedYear === 'all' || h.dataset.year === selectedYear) ? '' : 'none';
  }});
}}
</script>
"""

html = render_shell("Tâches", "tasks.html", body_content, page_style)

# ─── write ────────────────────────────────────────────────────────────────────

out_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "exports", "view"))
os.makedirs(out_dir, exist_ok=True)
out_path = os.path.join(out_dir, "tasks.html")

with open(out_path, "w", encoding="utf-8") as f:
    f.write(html)

print(f"\n── tasks ──")
print(f"mois chargés : {total_months}")
print(f"jours total  : {total_days_all:g}")
for p in projects:
    billed_ids = {id(t) for b in p.bills for t in b.tasks}
    billed   = sum(t.getTimeSpent() for t in p.tasks if id(t) in billed_ids and t.getTimeSpent() > 0)
    unbilled = sum(t.getTimeSpent() for t in p.tasks if id(t) not in billed_ids and t.getTimeSpent() > 0)
    zero     = sum(1 for t in p.tasks if t.getTimeSpent() == 0)
    print(f"  {p.uid:<20} tâches:{len(p.tasks):>3}  facturés:{billed:>5.1f}j  non-facturés:{unbilled:>5.1f}j  zéro:{zero}")
print(f"\nview @ {out_path}")

if hasattr(os, "startfile") and not configs.webview_mode:
    os.startfile(os.path.normpath(out_path))

if configs.pause_on_exit and not configs.webview_mode: input("\nEntrée pour fermer...")
