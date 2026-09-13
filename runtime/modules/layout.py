"""
Shared page shell for exports/view/*.html.

Every view_*.py script still builds its own body content and its own
page-specific CSS (tabs, calendar grid, whatever that page needs) — this
module only wraps that content with a nav header (links to every generated
page, plus an auto-refresh toggle) and a footer, so pages generated
independently can navigate to one another once opened in the webview (or a
plain browser).

Nav clicks go through navigateTo() below. Inside the webview (app_gui.py
injects a `pywebview.api`), that calls back into Python: when auto-refresh is
ON (default) it re-runs the target page's view_*.py before showing it; when
OFF it shows the last generated file as-is, only running the script if that
file doesn't exist yet. Opened as a plain file outside the webview (no
`pywebview.api` present), links just fall back to a normal navigation to the
last generated file.

Every <table> with a <thead>/<tbody> is made sortable automatically (see
SORT_SCRIPT): clicking a header sorts ascending, clicking again reverses,
`.total-row` rows always stay pinned at the bottom. A table can declare which
column it opens sorted by via `<table data-default-sort="colIndex:asc">` (dir
is "asc" or "desc", 0-based column index) — but as soon as a viewer clicks any
header in that table, their choice of column is remembered (per page, per
table, in localStorage) and takes over as the ASC default on the next page
open, overriding data-default-sort.
"""

# (filename, nav label, generating script) — filename must match what each
# view_*.py writes under exports/view/; script is the file app_gui.py runs to
# (re)generate it. Order here is the order shown in the nav.
PAGES = [
    ("homepage.html",       "Accueil",         "view_homepage.py"),
    ("billing.html",        "Facturation",     "view_billing.py"),
    ("tva.html",            "TVA",             "view_tva.py"),
    ("trimester.html",      "Trimestres",      "view_trimester.py"),
    ("tasks.html",          "Tâches",          "view_tasks.py"),
    ("tasks_calendar.html", "Calendrier",      "view_tasks_calendar.py"),
    ("wiring.html",         "Virements",       "view_wiring.py"),
]

NAV_CSS = """
  body { padding: 0 !important; margin: 0 !important; }
  .app-nav { display: flex; align-items: center; gap: 4px; flex-wrap: wrap;
             padding: 0 24px; height: 52px; background: #1c1c1c;
             position: sticky; top: 0; z-index: 1000; }
  .app-nav .brand { color: #fff; font-weight: 700; font-size: 14px;
                     margin-right: 20px; letter-spacing: .02em; white-space: nowrap; }
  .app-nav a { color: #aaa; text-decoration: none; font-size: 13px;
               padding: 7px 12px; border-radius: 6px;
               transition: background .15s, color .15s; }
  .app-nav a:hover { background: #333; color: #fff; }
  .app-nav a.active { background: #fff; color: #1c1c1c; font-weight: 600; }
  .app-nav .nav-spacer { flex: 1; }
  .icon-toggle { background: none; border: none; color: #888;
                 display: inline-flex; align-items: center; justify-content: center;
                 padding: 6px 10px; border-radius: 6px;
                 cursor: pointer; transition: background .15s, color .15s; }
  .icon-toggle:hover { background: #333; color: #fff; }
  .icon-toggle.active { color: #4caf50; }
  .app-body { padding: 24px 32px; }
  .app-footer { padding: 16px 32px; color: #aaa; font-size: 11px;
                text-align: center; border-top: 1px solid #e5e5e5; margin-top: 40px; }
  .app-footer a { color: #aaa; margin-left: 10px; }
  .app-footer a:hover { color: #666; }
  .error-banner { display: none; background: #c62828; color: #fff;
                  padding: 10px 24px; font-size: 13px; font-weight: 600; }

  /* sortable table headers (see SORT_SCRIPT) */
  th.sortable-th { cursor: pointer; user-select: none; }
  th.sortable-th:hover { color: #444; }
  th.sortable-th .sort-arrow { display: inline-block; margin-left: 4px; font-size: 9px; opacity: .35; }
  th.sortable-th .sort-arrow::after { content: '▲▼'; }
  th.sortable-th.sort-asc .sort-arrow, th.sortable-th.sort-desc .sort-arrow { opacity: 1; }
  th.sortable-th.sort-asc .sort-arrow::after { content: '▲'; }
  th.sortable-th.sort-desc .sort-arrow::after { content: '▼'; }

  .icon-toggle .spin { animation: icon-spin 1s linear infinite; }
  @keyframes icon-spin { to { transform: rotate(360deg); } }
"""

SORT_SCRIPT = """
function sortStorageKey(tableIndex) {
  return 'sortCol::' + location.pathname + '::' + tableIndex;
}

function initSortableTables() {
  document.querySelectorAll('table').forEach(function (table, tableIndex) {
    const thead = table.querySelector('thead');
    const tbody = table.querySelector('tbody');
    if (!thead || !tbody) return;
    const headerRow = thead.querySelector('tr');
    if (!headerRow) return;
    const headers = Array.from(headerRow.children);
    headers.forEach(function (th, colIndex) {
      th.classList.add('sortable-th');
      const arrow = document.createElement('span');
      arrow.className = 'sort-arrow';
      th.appendChild(arrow);
      th.addEventListener('click', function () {
        sortTableByColumn(tbody, colIndex, headers, th);
        try { localStorage.setItem(sortStorageKey(tableIndex), String(colIndex)); } catch (e) {}
      });
    });

    // initial sort on page open: remembered column (always ASC) takes
    // priority over the page's declared default (data-default-sort="col:dir")
    let initCol = null, initDir = 1;
    let remembered = null;
    try { remembered = localStorage.getItem(sortStorageKey(tableIndex)); } catch (e) {}
    if (remembered !== null && headers[parseInt(remembered, 10)]) {
      initCol = parseInt(remembered, 10);
      initDir = 1;
    } else if (table.dataset.defaultSort) {
      const parts = table.dataset.defaultSort.split(':');
      const col = parseInt(parts[0], 10);
      if (headers[col]) {
        initCol = col;
        initDir = parts[1] === 'desc' ? -1 : 1;
      }
    }
    if (initCol !== null) {
      sortTableByColumn(tbody, initCol, headers, headers[initCol], initDir);
    }
  });
}

function extractDate(text) {
  const m = text.match(/\\d{4}-\\d{2}-\\d{2}/);
  return m ? m[0] : null;
}

function extractNumber(text) {
  const m = text.match(/-?\\d{1,3}(?:[ \\u00A0]\\d{3})*(?:[.,]\\d+)?/);
  if (!m) return null;
  let s = m[0].replace(/[ \\u00A0]/g, '');
  if (s.includes(',')) s = s.replace(',', '.');
  const n = parseFloat(s);
  return isNaN(n) ? null : n;
}

function sortTableByColumn(tbody, colIndex, headers, clickedTh, forcedDir) {
  const allRows = Array.from(tbody.querySelectorAll('tr'));
  const pinnedRows = allRows.filter(r => r.classList.contains('total-row'));
  const otherRows  = allRows.filter(r => !r.classList.contains('total-row') && r.querySelector('td[colspan]'));
  const sortableRows = allRows.filter(r => !r.classList.contains('total-row') && !r.querySelector('td[colspan]'));

  const dir = forcedDir || (clickedTh.classList.contains('sort-asc') ? -1 : 1);

  headers.forEach(h => h.classList.remove('sort-asc', 'sort-desc'));
  clickedTh.classList.add(dir === 1 ? 'sort-asc' : 'sort-desc');

  sortableRows.sort(function (r1, r2) {
    const c1 = r1.children[colIndex], c2 = r2.children[colIndex];
    if (!c1 || !c2) return 0;
    const t1 = c1.textContent.trim(), t2 = c2.textContent.trim();
    const d1 = extractDate(t1), d2 = extractDate(t2);
    if (d1 !== null && d2 !== null) return dir * d1.localeCompare(d2);
    const n1 = extractNumber(t1), n2 = extractNumber(t2);
    if (n1 !== null && n2 !== null) return dir * (n1 - n2);
    return dir * t1.localeCompare(t2, 'fr', { numeric: true, sensitivity: 'base' });
  });

  sortableRows.concat(otherRows, pinnedRows).forEach(r => tbody.appendChild(r));
}
"""

NAV_SCRIPT = """
function restartApp() {
  if (window.pywebview && window.pywebview.api) {
    window.pywebview.api.restart();
  }
  return false;
}
const ICON_ARCHIVE = '<svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor"><path d="M20.54 5.23l-1.39-1.68C18.88 3.21 18.47 3 18 3H6c-.47 0-.88.21-1.16.55L3.46 5.23C3.17 5.57 3 6.02 3 6.5V19c0 1.1.9 2 2 2h14c1.1 0 2-.9 2-2V6.5c0-.48-.17-.93-.46-1.27zM12 17.5L6.5 12H10v-2h4v2h3.5L12 17.5zM5.12 5l.81-1h12.14l.81 1H5.12z"/></svg>';
const ICON_SPINNER = '<svg class="spin" width="16" height="16" viewBox="0 0 24 24" fill="currentColor"><path d="M12 4V1L8 5l4 4V6c3.31 0 6 2.69 6 6 0 1.01-.25 1.97-.7 2.8l1.46 1.46A7.93 7.93 0 0 0 20 12c0-4.42-3.58-8-8-8zm0 14c-3.31 0-6-2.69-6-6 0-1.01.25-1.97.7-2.8L5.24 7.74A7.93 7.93 0 0 0 4 12c0 4.42 3.58 8 8 8v3l4-4-4-4v3z"/></svg>';
const ICON_CHECK = '<svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor"><path d="M9 16.2 4.8 12l-1.4 1.4L9 19 21 7l-1.4-1.4z"/></svg>';
const ICON_CROSS = '<svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor"><path d="M18.3 5.71 12 12l6.3 6.29-1.41 1.42L10.59 13.4 4.3 19.71 2.89 18.3 9.18 12 2.89 5.71 4.3 4.29l6.29 6.3 6.29-6.3z"/></svg>';
function backupDatabase() {
  if (!(window.pywebview && window.pywebview.api)) return false;
  const btn = document.getElementById('backup-btn');
  const revert = () => { btn.disabled = false; btn.innerHTML = ICON_ARCHIVE; btn.title = 'Exporter la base de données (zip)'; };
  btn.disabled = true;
  btn.innerHTML = ICON_SPINNER;
  window.pywebview.api.backup_database().then(function (result) {
    if (result && result.ok) {
      btn.innerHTML = ICON_CHECK;
      btn.title = 'Zip créé : ' + result.path;
    } else {
      btn.innerHTML = ICON_CROSS;
      btn.title = 'Échec de l\\'export : ' + (result && result.error || '?');
    }
    setTimeout(revert, 2500);
  });
  return false;
}
function navigateTo(file) {
  if (window.pywebview && window.pywebview.api) {
    document.body.style.cursor = 'wait';
    window.pywebview.api.navigate(file).then(function () {
      window.location.href = file;
    });
  } else {
    window.location.href = file;
  }
  return false;
}
let autoRefreshOn = true;
function updateAutoRefreshBtn() {
  const btn = document.getElementById('auto-refresh-btn');
  btn.classList.toggle('active', autoRefreshOn);
  btn.title = 'Auto refresh : ' + (autoRefreshOn ? 'activé' : 'désactivé');
}
function toggleAutoRefresh() {
  autoRefreshOn = !autoRefreshOn;
  updateAutoRefreshBtn();
  if (window.pywebview && window.pywebview.api) {
    window.pywebview.api.set_auto_refresh(autoRefreshOn);
  }
}
window.addEventListener('pywebviewready', function () {
  window.pywebview.api.get_auto_refresh().then(function (value) {
    autoRefreshOn = value;
    updateAutoRefreshBtn();
  });
  window.pywebview.api.get_error(CURRENT_FILE).then(function (message) {
    if (!message) return;
    const banner = document.getElementById('error-banner');
    banner.textContent = 'Erreur lors de la génération de cette page : ' + message;
    banner.style.display = 'block';
  });
});
initSortableTables();
"""


def render_shell(title, active_file, body_html, extra_style=""):
    """
    Wrap page content with the shared nav header + footer.

    title       -- <title> text
    active_file -- filename (must be one of PAGES) of the page being built,
                   used to highlight the current entry in the nav
    body_html   -- the page's own content (h1, meta line, tables, tabs, its
                   own <script> block, etc.) — no outer html/head/body tags
    extra_style -- the page's own <style> rules (without the <style> tags)
    """
    nav_links = "".join(
        f'<a href="{f}" onclick="return navigateTo(\'{f}\')"{" class=\"active\"" if f == active_file else ""}>{label}</a>'
        for f, label, _script in PAGES
    )

    return f"""<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8"/>
<title>{title}</title>
<style>
{NAV_CSS}
{extra_style}
</style>
</head>
<body>

<nav class="app-nav">
  <span class="brand">compta_python</span>
  {nav_links}
  <span class="nav-spacer"></span>
  <button id="backup-btn" class="icon-toggle" onclick="return backupDatabase()" title="Exporter la base de données (zip)">
    <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor"><path d="M20.54 5.23l-1.39-1.68C18.88 3.21 18.47 3 18 3H6c-.47 0-.88.21-1.16.55L3.46 5.23C3.17 5.57 3 6.02 3 6.5V19c0 1.1.9 2 2 2h14c1.1 0 2-.9 2-2V6.5c0-.48-.17-.93-.46-1.27zM12 17.5L6.5 12H10v-2h4v2h3.5L12 17.5zM5.12 5l.81-1h12.14l.81 1H5.12z"/></svg>
  </button>
  <button id="auto-refresh-btn" class="icon-toggle active" onclick="toggleAutoRefresh()" title="Auto refresh : activé">
    <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor"><path d="M17.65 6.35A7.958 7.958 0 0 0 12 4c-4.42 0-7.99 3.58-7.99 8s3.57 8 7.99 8c3.73 0 6.84-2.55 7.73-6h-2.08c-.82 2.33-3.04 4-5.65 4-3.31 0-6-2.69-6-6s2.69-6 6-6c1.66 0 3.14.69 4.22 1.78L13 11h7V4l-2.35 2.35z"/></svg>
  </button>
</nav>

<div id="error-banner" class="error-banner"></div>

<div class="app-body">
{body_html}
</div>

<div class="app-footer">
  compta_python — vue générée localement
  <a href="#" onclick="return restartApp()">Redémarrer l'application</a>
</div>

<script>
const CURRENT_FILE = "{active_file}";
{SORT_SCRIPT}
{NAV_SCRIPT}
</script>

</body>
</html>"""
