"""
Generate exports/view/tasks_calendar.html — monthly calendar view.

One tab per month. Each day cell shows project entries with time spent.
"""

import locale
import sys
import traceback

import configs

def _excepthook(etype, value, tb):
    traceback.print_exception(etype, value, tb)
    if configs.pause_on_exit and not configs.webview_mode: input("\nEntrée pour fermer...")
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
from modules.layout import render_shell

# ─── load ─────────────────────────────────────────────────────────────────────

db = Database.init_billing()

# ─── assign a stable color per project ────────────────────────────────────────

OFF_COLOR   = "#b3e5fc"   # light blue — reserved for off/congé days

PALETTE = [
    "#ffadad", "#ffd6a5", "#fdffb6", "#caffbf", "#9bf6ff",
    "#a0c4ff", "#bdb2ff", "#ffc6ff", "#fffffc", "#b5ead7",
    "#f9c6c9", "#fce38a", "#95e1d3", "#c9b1ff", "#ffd3b6",
    "#dcedc1", "#a8e6cf", "#ffd3e0", "#d4f1f4", "#e8d5f5",
]

# stable assignment: sort projects by uid for determinism, assign palette index
# unless the project defines its own color:#hex
project_colors = {}
for i, p in enumerate(sorted(db.projects, key=lambda x: x.uid)):
    project_colors[p.uid] = p.color or PALETTE[i % len(PALETTE)]

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

for t in db.tasks:
    if t.is_off:
        d = t.date.date() if hasattr(t.date, 'date') else t.date
        by_date[d].append({
            "uid":   "off",
            "name":  "Congé",
            "days":  t.getTimeSpent(),
            "color": OFF_COLOR,
        })

# sort entries within each day by days desc
for d in by_date:
    by_date[d].sort(key=lambda x: -x["days"])

# ─── months with data ─────────────────────────────────────────────────────────

months_with_data = sorted({d.strftime("%Y-%m") for d in by_date.keys()}, reverse=True)
print(f"dates chargées : {len(by_date)}  —  mois : {months_with_data[:3]}...")

# ─── helpers ──────────────────────────────────────────────────────────────────

DAY_HEADERS = ["Lun", "Mar", "Mer", "Jeu", "Ven", "Sam", "Dim"]

def th(*cols):
    return "<tr>" + "".join(f"<th>{c}</th>" for c in cols) + "</tr>"

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
            if e["uid"] != "off":
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

    off_total = sum(
        e["days"]
        for d, entries in by_date.items()
        if d.year == year and d.month == month
        for e in entries if e["uid"] == "off"
    )
    if off_total > 0:
        legend += f'<div class="legend-item off-legend"><span class="legend-dot" style="background:{OFF_COLOR}"></span>Congé<span class="legend-days">{fmt_days(off_total)}</span></div>'

    headers = "".join(f'<div class="day-header">{h}</div>' for h in DAY_HEADERS)

    state_legend = f"""
    <div class="state-legend">
      <span class="state-item"><span class="state-swatch" style="background:#f0f0f0"></span>Aucune tâche</span>
      <span class="state-item"><span class="state-swatch" style="background:#fafafa;border:1px solid #eee"></span>Weekend</span>
      <span class="state-item"><span class="state-swatch" style="background:#fffbe6"></span>Aujourd'hui</span>
      <span class="state-item"><span class="state-swatch" style="background:#fdecea"></span>Jour × 0</span>
      <span class="state-item"><span class="state-swatch" style="background:{OFF_COLOR}"></span>Congé</span>
    </div>"""

    return f"""
    <div class="legend">{legend}</div>
    {state_legend}
    <div class="cal-grid">
      <div class="day-headers">{headers}</div>
      <div class="days">{grid}</div>
    </div>"""

# ─── build tabs ───────────────────────────────────────────────────────────────

MONTH_ABBR = ["Jan","Fév","Mar","Avr","Mai","Jun","Jul","Aoû","Sep","Oct","Nov","Déc"]

current_year = date.today().year

# every month of the current year is selectable (even with no data yet, so
# the calendar import can fill in months that haven't been tracked locally
# at all) -- past years stay limited to months that actually have data
years_available = defaultdict(set)
for ym in months_with_data:
    y, m = int(ym[:4]), int(ym[5:])
    years_available[y].add(m)
years_available[current_year].update(range(1, 13))

years_sorted = sorted(years_available.keys(), reverse=True)

sel_year, sel_month = current_year, date.today().month

all_yms = sorted(set(months_with_data) | {f"{current_year}-{m:02d}" for m in range(1, 13)}, reverse=True)

tabs_content = ""
for ym in all_yms:
    tid = f"tab-{ym}"
    active = "active" if ym == f"{sel_year}-{sel_month:02d}" else ""
    content = render_month(ym) if ym in months_with_data else '<div class="cal-empty">Aucune tâche déclarée</div>'
    tabs_content += f'<div class="tab-panel {active}" id="{tid}">{content}</div>'

years_nav = ""
for y in years_sorted:
    active = "active" if y == sel_year else ""
    years_nav += f'<button class="tab-btn year-btn {active}" onclick="selectYear({y})" id="btn-year-{y}">{y}</button>'

months_nav = ""
for m in range(1, 13):
    active = "active" if m == sel_month else ""
    months_nav += f'<button class="tab-btn month-btn {active}" onclick="selectMonth({m})" id="btn-month-{m}">{MONTH_ABBR[m-1]}</button>'

years_data_js = "{" + ",".join(f'"{y}":[{",".join(str(m) for m in sorted(ms))}]' for y, ms in years_available.items()) + "}"

# ─── google calendar import preview ────────────────────────────────────────────
# Fetched on demand only (button click below) — never on page open, since the
# network round-trip can be slow.

CALENDAR_PREVIEW_SCRIPT = """
function escHtml(s) {
  return String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
}
function activeYm() {
  return selectedYear + '-' + String(selectedMonth).padStart(2, '0');
}

let lastRows = [];
let showIgnored = false;

function rowClass(r) {
  if (r.status === 'UNMATCHED') return 'cal-unmatched';
  if (r.status === 'ignored') return 'cal-ignored';
  if (r.local === 'conflict') return 'cal-local-conflict';
  if (r.local === 'match') return 'cal-local-match';
  if (r.status === 'alias') return 'cal-ignored';   // off, not yet resolved either way
  return '';
}

function isGrayed(r) {
  return rowClass(r) === 'cal-ignored';
}

function toggleShowIgnored() {
  showIgnored = document.getElementById('cal-show-ignored').checked;
  renderRows();
  return false;
}

function rowAction(r, i) {
  if (r.local === 'match') return '<span class="cal-local-label">Déjà présent</span>';
  if (r.local === 'conflict') return '<button class="cal-row-import cal-row-replace" onclick="return importRow(' + i + ')">Remplacer</button>';
  if (r.local === 'new') return '<button class="cal-row-import" onclick="return importRow(' + i + ')">Importer</button>';
  return '';
}

function renderRows() {
  const tbody = document.getElementById('cal-preview-tbody');
  tbody.innerHTML = lastRows.map(function (r, i) {
    const hiddenAttr = (isGrayed(r) && !showIgnored) ? ' hidden' : '';
    return '<tr class="' + rowClass(r) + '"' + hiddenAttr + '>' +
      '<td>' + r.date + ' (' + r.weekday + ')</td>' +
      '<td>' + escHtml(r.title) + '</td>' +
      '<td>' + (r.uid || '?') + '</td>' +
      '<td class="num">' + r.fraction + '</td>' +
      '<td>' + r.status + '</td>' +
      '<td>' + rowAction(r, i) + '</td>' +
      '</tr>';
  }).join('');

  const banner = document.getElementById('cal-conflict-banner');
  const conflicts = lastRows.filter(function (r) { return r.local === 'conflict'; }).length;
  if (conflicts > 0) {
    banner.textContent = conflicts + ' différence(s) à traiter';
    banner.style.display = '';
  } else {
    banner.style.display = 'none';
  }
}

function updateImportAllVisibility() {
  const allBtn = document.getElementById('cal-import-all-btn');
  allBtn.style.display = lastRows.some(function (r) { return r.local === 'new'; }) ? '' : 'none';
}

function loadCalendarPreview() {
  const btn = document.getElementById('cal-preview-btn');
  const summary = document.getElementById('cal-preview-summary');
  if (!(window.pywebview && window.pywebview.api)) {
    summary.textContent = "Indisponible en dehors de l'application.";
    return false;
  }
  const ym = activeYm();
  btn.disabled = true;
  btn.textContent = 'Chargement…';
  summary.textContent = '';
  lastRows = [];
  renderRows();
  document.getElementById('cal-import-all-btn').style.display = 'none';
  window.pywebview.api.fetch_calendar_preview(ym).then(function (result) {
    btn.disabled = false;
    btn.textContent = "Recharger l'aperçu (" + ym + ")";
    if (!result || !result.ok) {
      summary.textContent = 'Erreur : ' + (result && result.error || '?');
      return;
    }
    if (result.rows.length === 0) {
      summary.textContent = 'Aucun événement trouvé sur ce mois.';
      return;
    }
    lastRows = result.rows;
    renderRows();
    updateImportAllVisibility();
    const unmatched = lastRows.filter(function (r) { return r.status === 'UNMATCHED'; }).length;
    summary.textContent = lastRows.length + ' événement(s) — ' + unmatched + ' non résolu(s)';
  });
  return false;
}

async function importRow(i) {
  const r = lastRows[i];
  if (!r || !(window.pywebview && window.pywebview.api)) return false;
  let replace = false;
  if (r.local === 'conflict') {
    const msg = 'Le projet "' + r.uid + '" est déjà déclaré le ' + r.date +
      ' avec ' + r.existing_fraction + ' j (calendrier : ' + r.fraction + ' j).\\n\\n' +
      'Voulez-vous remplacer la donnée existante ?';
    if (!confirm(msg)) return false;
    replace = true;
  } else if (r.local !== 'new') {
    return false;
  }
  const result = await window.pywebview.api.import_calendar_entry(activeYm(), r.date, r.uid, r.fraction, replace);
  if (result && result.ok) {
    r.local = 'match';
    r.existing_fraction = r.fraction;
    renderRows();
    updateImportAllVisibility();
    await reloadAfterImport();
  } else if (result && result.conflict) {
    alert("Le fichier a changé entre-temps, rechargez l'aperçu avant de réessayer.");
  } else {
    alert('Échec import : ' + (result && result.error || '?'));
  }
  return false;
}

async function reloadAfterImport() {
  if (!(window.pywebview && window.pywebview.api)) return;
  document.body.style.cursor = 'wait';
  try {
    await window.pywebview.api.run('tasks_calendar.html');
  } catch (e) {}
  window.location.reload();
}

async function importAllRows() {
  const allBtn = document.getElementById('cal-import-all-btn');
  const summary = document.getElementById('cal-preview-summary');
  if (!(window.pywebview && window.pywebview.api)) return false;
  allBtn.disabled = true;
  allBtn.textContent = 'Import en cours…';
  const conflicts = lastRows.filter(function (r) { return r.local === 'conflict'; }).length;
  let added = 0, failed = 0;
  for (let i = 0; i < lastRows.length; i++) {
    const r = lastRows[i];
    if (r.local !== 'new') continue;   // conflicts need a manual, per-row decision
    const result = await window.pywebview.api.import_calendar_entry(activeYm(), r.date, r.uid, r.fraction, false);
    if (result && result.ok) {
      r.local = 'match';
      r.existing_fraction = r.fraction;
      added++;
    } else {
      failed++;
    }
  }
  renderRows();
  allBtn.disabled = false;
  allBtn.textContent = "Importer tout";
  updateImportAllVisibility();
  let msg = added + ' ajouté(s)';
  if (conflicts) msg += ', ' + conflicts + ' conflit(s) à traiter manuellement';
  if (failed) msg += ', ' + failed + ' échec(s)';
  summary.textContent = msg;
  if (added > 0) await reloadAfterImport();
  return false;
}

function resetCalendarPreview() {
  const btn = document.getElementById('cal-preview-btn');
  if (!btn || btn.disabled) return;  // don't clobber a fetch in progress
  btn.textContent = "Charger l'aperçu (" + activeYm() + ")";
  document.getElementById('cal-preview-summary').textContent = '';
  lastRows = [];
  renderRows();
  document.getElementById('cal-import-all-btn').style.display = 'none';
}
"""

# ─── assemble ─────────────────────────────────────────────────────────────────

generated_at = datetime.now().strftime("%Y-%m-%d %H:%M")

page_style = """
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { font-family: system-ui, sans-serif; font-size: 13px; background: #f5f5f5; color: #222; }
  h1 { font-size: 20px; font-weight: 700; margin-bottom: 4px; }
  .meta { color: #888; font-size: 12px; margin-bottom: 20px; }

  /* tabs */
  .tabs-nav { display: flex; flex-wrap: wrap; gap: 6px; margin-bottom: 20px; }
  .tab-btn { padding: 6px 14px; border: 1px solid #ddd; border-radius: 20px;
              background: #fff; cursor: pointer; font-size: 12px; font-weight: 500;
              color: #555; transition: background .15s; }
  .tab-btn:hover { background: #f0f0f0; }
  .tab-btn.active { background: #222; color: #fff; border-color: #222; }
  .tab-btn.disabled { opacity: .3; pointer-events: none; }
  .tab-panel { display: none; }
  .tab-panel.active { display: block; }

  /* legend */
  .legend { display: flex; flex-wrap: wrap; gap: 10px 20px; margin-bottom: 16px; }
  .legend-item { display: flex; align-items: center; gap: 6px; font-size: 12px; color: #555; }
  .legend-dot { width: 10px; height: 10px; border-radius: 50%; flex-shrink: 0; }
  .legend-days { margin-left: 6px; font-weight: 600; color: #333; }
  .total-legend { font-weight: 700; color: #222; }

  /* calendar */
  .cal-grid { background: #fff; border-radius: 10px; box-shadow: 0 1px 4px rgba(0,0,0,.08); overflow: hidden; }
  .cal-empty { background: #fff; border-radius: 10px; box-shadow: 0 1px 4px rgba(0,0,0,.08);
                padding: 60px 20px; text-align: center; color: #bbb; font-size: 14px; font-weight: 600; }
  .day-headers { display: grid; grid-template-columns: repeat(7, 1fr);
                  background: #f7f7f7; border-bottom: 1px solid #eee; }
  .day-header { padding: 8px; text-align: center; font-size: 11px; font-weight: 600;
                 text-transform: uppercase; letter-spacing: .05em; color: #aaa; }
  .days { display: grid; grid-template-columns: repeat(7, 1fr); }
  .day-cell { height: 90px; padding: 6px; border-right: 1px solid #f0f0f0;
               border-bottom: 1px solid #f0f0f0; display: flex; flex-direction: column; }
  .day-cell.empty { background: #fafafa; }
  .day-cell.weekend { background: #fafafa; }
  .day-cell.today { background: #fffbe6; }
  .day-cell:nth-child(7n) { border-right: none; }
  .day-num { font-size: 11px; font-weight: 700; color: #bbb; margin-bottom: 4px; flex-shrink: 0; }
  .today .day-num { color: #e65100; }
  .weekend .day-num { color: #ddd; }

  /* stacked bar */
  .bar-wrap { flex: 1; border-radius: 4px; overflow: hidden; display: flex;
               flex-direction: column; background: #f0f0f0; min-height: 0; }
  .bar-seg { width: 100%; transition: opacity .15s; position: relative;
              display: flex; align-items: center; overflow: hidden; }
  .bar-seg:hover { opacity: .75; cursor: default; }
  .zero-seg { background: #fdecea !important; }
  .bar-label { font-size: 9px; font-weight: 600; color: rgba(0,0,0,.6);
                padding: 0 4px; white-space: nowrap; overflow: hidden;
                text-overflow: ellipsis; pointer-events: none; }

  .day-total { font-size: 9px; font-weight: 700; color: #bbb; text-align: right;
                margin-top: 3px; flex-shrink: 0; }

  /* state legend */
  .state-legend { display: flex; gap: 16px; flex-wrap: wrap; margin-bottom: 12px; }
  .state-item { display: flex; align-items: center; gap: 6px; font-size: 11px; color: #888; }
  .state-swatch { display: inline-block; width: 14px; height: 14px; border-radius: 3px;
                   border: 1px solid #e0e0e0; flex-shrink: 0; }

  /* google calendar import preview */
  h2 { font-size: 15px; font-weight: 700; margin: 32px 0 10px; }
  table { width: 100%; border-collapse: collapse; background: #fff; border-radius: 8px;
            overflow: hidden; box-shadow: 0 1px 3px rgba(0,0,0,.07); margin-bottom: 4px; }
  th { background: #f0f0f0; text-align: left; padding: 7px 12px;
        font-size: 10px; text-transform: uppercase; letter-spacing: .05em; color: #888; }
  td { padding: 7px 12px; border-top: 1px solid #f0f0f0; vertical-align: middle; }
  tr:hover td { background: #fafafa; }
  .num { text-align: left; font-variant-numeric: tabular-nums; white-space: nowrap; }
  tr.cal-unmatched td { background: #fdecea; }
  tr.cal-fuzzy td { background: #fff8e1; }
  tr.cal-ignored td { color: #bbb; }
  tr.cal-local-match td { background: #eaf7ea; }
  tr.cal-local-conflict td { background: #fff1e0; }
  .cal-local-label { color: #4a8a4a; font-size: 11px; font-weight: 600; }
  #cal-preview-btn, #cal-import-all-btn { padding: 7px 16px; border: none; border-radius: 20px;
                      background: #222; color: #fff; cursor: pointer; font-size: 12px;
                      font-weight: 600; }
  #cal-preview-btn:hover, #cal-import-all-btn:hover { background: #444; }
  #cal-preview-btn:disabled, #cal-import-all-btn:disabled { opacity: .5; cursor: default; }
  #cal-import-all-btn { background: #2e7d32; margin-left: 8px; }
  #cal-import-all-btn:hover { background: #256428; }
  #cal-preview-summary { margin-left: 12px; color: #888; font-size: 12px; }
  .cal-row-import { padding: 4px 10px; border: none; border-radius: 14px;
                     background: #222; color: #fff; cursor: pointer; font-size: 11px; font-weight: 600; }
  .cal-row-import:hover { background: #444; }
  .cal-row-replace { background: #d97706; }
  .cal-row-replace:hover { background: #b45f04; }
  .cal-conflict-banner { display: inline-block; margin-bottom: 8px; padding: 6px 14px;
                           border-radius: 20px; background: #fff1e0; color: #b45f04;
                           font-size: 12px; font-weight: 600; }
  .cal-toggle-ignored { display: inline-flex; align-items: center; gap: 5px;
                          margin-left: 12px; font-size: 12px; color: #888; cursor: pointer; }
"""

body_content = f"""
<h1>Tasks — calendrier</h1>
<div class="meta">Généré le {generated_at}</div>

<div class="tabs-nav">{months_nav}</div>
<div class="tabs-nav">{years_nav}</div>

{tabs_content}

<h2>Import Google Calendar — aperçu</h2>
<div class="meta">
  <button id="cal-preview-btn" onclick="return loadCalendarPreview()">Charger l'aperçu ({sel_year}-{sel_month:02d})</button>
  <button id="cal-import-all-btn" onclick="return importAllRows()" style="display:none">Importer tout</button>
  <label class="cal-toggle-ignored">
    <input type="checkbox" id="cal-show-ignored" onchange="return toggleShowIgnored()">
    Afficher les jours ignorés
  </label>
  <span id="cal-preview-summary"></span>
</div>
<div id="cal-conflict-banner" class="cal-conflict-banner" style="display:none"></div>
<table id="cal-preview-table" data-default-sort="0:asc">
  <thead>{th("Date", "Titre calendrier", "Projet", "Fraction", "Statut", "Action")}</thead>
  <tbody id="cal-preview-tbody"></tbody>
</table>

<script>{CALENDAR_PREVIEW_SCRIPT}</script>

<script>
const YEARS_DATA = {years_data_js};
let selectedYear = {sel_year};
let selectedMonth = {sel_month};

// restore the last month the user was viewing (e.g. across the reload that
// follows a calendar import) instead of always defaulting to today's month
try {{
  const saved = localStorage.getItem('calendrier::lastMonth');
  if (saved) {{
    const parts = saved.split('-');
    const y = parseInt(parts[0], 10), m = parseInt(parts[1], 10);
    if (YEARS_DATA[y] && YEARS_DATA[y].includes(m)) {{
      selectedYear = y;
      selectedMonth = m;
    }}
  }}
}} catch (e) {{}}

function render() {{
  try {{ localStorage.setItem('calendrier::lastMonth', selectedYear + '-' + String(selectedMonth).padStart(2, '0')); }} catch (e) {{}}
  document.querySelectorAll('.tab-panel').forEach(p => p.classList.remove('active'));
  const ym = selectedYear + '-' + String(selectedMonth).padStart(2, '0');
  const panel = document.getElementById('tab-' + ym);
  if (panel) panel.classList.add('active');

  document.querySelectorAll('.year-btn').forEach(b => b.classList.remove('active'));
  document.getElementById('btn-year-' + selectedYear).classList.add('active');

  document.querySelectorAll('.month-btn').forEach(b => {{
    b.classList.remove('active');
    b.classList.remove('disabled');
  }});
  document.getElementById('btn-month-' + selectedMonth).classList.add('active');

  const available = YEARS_DATA[selectedYear] || [];
  for (let m = 1; m <= 12; m++) {{
    if (!available.includes(m)) {{
      document.getElementById('btn-month-' + m).classList.add('disabled');
    }}
  }}

  resetCalendarPreview();
}}

function selectYear(y) {{
  selectedYear = y;
  const available = YEARS_DATA[y] || [];
  if (!available.includes(selectedMonth)) {{
    selectedMonth = available[available.length - 1];
  }}
  render();
}}

function selectMonth(m) {{
  const available = YEARS_DATA[selectedYear] || [];
  if (!available.includes(m)) return;
  selectedMonth = m;
  render();
}}

render();
</script>
"""

html = render_shell("Tasks calendrier", "tasks_calendar.html", body_content, page_style)

# ─── write ────────────────────────────────────────────────────────────────────

out_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "exports", "view"))
os.makedirs(out_dir, exist_ok=True)
out_path = os.path.join(out_dir, "tasks_calendar.html")

with open(out_path, "w", encoding="utf-8") as f:
    f.write(html)

print(f"\n── tasks_calendar ──")
print(f"mois : {len(months_with_data)}")
print(f"view @ {out_path}")

if hasattr(os, "startfile") and not configs.webview_mode:
    os.startfile(os.path.normpath(out_path))

if configs.pause_on_exit and not configs.webview_mode: input("\nEntrée pour fermer...")
