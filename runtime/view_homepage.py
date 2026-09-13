"""
Generate exports/view/homepage.html — landing page of the webview app.

Cards linking to every other view_*.py page (same list as the shared nav in
modules/layout.py), so this is the entry point when opening the app.
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
from datetime import datetime

import configs
from packages.database.database import Database
from modules.layout import render_shell

# ─── load ─────────────────────────────────────────────────────────────────────

db = Database.init_billing()

# ─── cards ────────────────────────────────────────────────────────────────────
# (filename, title, description) — filename must match modules/layout.PAGES

CARDS = [
    ("billing.html",        "Facturation",     "Factures, totaux HT/TVA/TTC, encaissements, jours facturés et non facturés."),
    ("tva.html",            "TVA",             "TVA à déclarer par mois, basé sur les encaissements (paiements reçus)."),
    ("trimester.html",      "Trimestres",      "Charges sociales (cotisations, CFP, versement libératoire) par trimestre."),
    ("tasks.html",          "Tâches",          "Jours travaillés par mois (tous projets), ou détail facturé/non-facturé par projet."),
    ("tasks_calendar.html", "Calendrier",      "Vue calendrier mensuelle des tâches, congés et jours chômés."),
    ("wiring.html",         "Virements",       "Virements reçus et rapprochement avec les factures émises."),
]

def card(href, title, desc):
    return f"""<a class="nav-card" href="{href}" onclick="return navigateTo('{href}')">
      <div class="nav-card-title">{title}</div>
      <div class="nav-card-desc">{desc}</div>
    </a>"""

cards_html = "".join(card(*c) for c in CARDS)

# ─── summary ──────────────────────────────────────────────────────────────────

summary = f"""<div class="cards">
  <div class="card"><div class="card-label">Projets</div><div class="card-value">{len(db.projects)}</div></div>
  <div class="card"><div class="card-label">Clients</div><div class="card-value">{len(db.clients)}</div></div>
</div>"""

# ─── assemble ─────────────────────────────────────────────────────────────────

generated_at = datetime.now().strftime("%Y-%m-%d %H:%M")

page_style = """
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { font-family: system-ui, sans-serif; font-size: 14px; background: #f5f5f5; color: #222; }
  h1 { font-size: 22px; font-weight: 700; margin-bottom: 4px; }
  .meta { color: #888; font-size: 12px; margin-bottom: 24px; }

  .cards { display: flex; gap: 12px; flex-wrap: wrap; margin-bottom: 32px; }
  .card { background: #fff; border-radius: 8px; padding: 14px 20px; min-width: 130px;
            box-shadow: 0 1px 3px rgba(0,0,0,.07); }
  .card-label { font-size: 10px; color: #aaa; text-transform: uppercase; letter-spacing: .05em; }
  .card-value { font-size: 20px; font-weight: 700; margin-top: 4px; }

  .nav-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(220px, 1fr)); gap: 14px; }
  .nav-card { display: block; background: #fff; border-radius: 10px; padding: 18px 20px;
              box-shadow: 0 1px 3px rgba(0,0,0,.07); text-decoration: none; color: inherit;
              transition: box-shadow .15s, transform .15s; }
  .nav-card:hover { box-shadow: 0 4px 12px rgba(0,0,0,.12); transform: translateY(-1px); }
  .nav-card-title { font-size: 15px; font-weight: 700; margin-bottom: 6px; }
  .nav-card-desc { font-size: 12px; color: #888; line-height: 1.4; }
"""

body_content = f"""
<h1>compta_python</h1>
<div class="meta">Généré le {generated_at}</div>

{summary}

<div class="nav-grid">{cards_html}</div>
"""

html = render_shell("Accueil", "homepage.html", body_content, page_style)

# ─── write ────────────────────────────────────────────────────────────────────

out_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "exports", "view"))
os.makedirs(out_dir, exist_ok=True)
out_path = os.path.join(out_dir, "homepage.html")

with open(out_path, "w", encoding="utf-8") as f:
    f.write(html)

print(f"\n── homepage ──")
print(f"projets : {len(db.projects)}")
print(f"clients : {len(db.clients)}")
print(f"view @ {out_path}")

if hasattr(os, "startfile") and not configs.webview_mode:
    os.startfile(os.path.normpath(out_path))

if configs.pause_on_exit and not configs.webview_mode: input("\nEntrée pour fermer...")
