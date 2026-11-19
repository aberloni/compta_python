"""
Generate exports/view/projects.html — vue d'ensemble des projets.

Tabs: "Tous" (default) — one row per project with its essential numbers.
One tab per project — summary cards, settings (client and taux history, TVA,
color), its bills with payment status, and worked/billed days per year.
Read-only: projects are edited in their projects/{uid}.proj file.
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
from collections import defaultdict

from packages.database.database import Database
from packages.database.wiring import Wiring
from packages.database.project import _parse_taux_entries
from modules.layout import render_shell

# ─── load ─────────────────────────────────────────────────────────────────────

db = Database.init_billing()
wiring = Wiring()

known_uids   = {c.uid for c in db.clients}
paid_by_fuid = wiring.payments_by_fuid(db, known_uids)

# ─── helpers ──────────────────────────────────────────────────────────────────

def fmt_eur(v):
    return f"{v:,.2f}&nbsp;€".replace(",", " ")

def fmt_days(v):
    return f"{v:g}&nbsp;j"

def card(label, value, cls=""):
    return f'<div class="card {cls}"><div class="card-label">{label}</div><div class="card-value">{value}</div></div>'

def th(*cols):
    return "<tr>" + "".join(f"<th>{c}</th>" for c in cols) + "</tr>"

def swatch(color):
    return f'<span class="swatch" style="background:{color}"></span>' if color else '<span class="swatch none"></span>'

def project_stats(p):
    """Essential numbers of one project, shared by the "Tous" table and its own tab."""
    tasks = p.tasks or []
    bills = p.bills or []
    billed_ids = {id(t) for b in bills for t in b.tasks}

    worked   = sum(t.getTimeSpent() for t in tasks)
    unbilled = sum(t.getTimeSpent() for t in tasks if id(t) not in billed_ids)
    billed   = sum(b.countDays() for b in bills)
    ht       = sum(b.getHT() for b in bills)
    ttc      = sum(b.getTTC() for b in bills)
    received = sum(pay.amount for b in bills for pay in paid_by_fuid.get(b.getFullUid() or b.uid, []))

    dates = [t.date for t in tasks]
    return {
        "worked": worked, "billed": billed, "unbilled": unbilled,
        "bills": len(bills), "ht": ht, "ttc": ttc,
        "received": received, "remaining": ttc - received,
        "first": min(dates) if dates else None,
        "last": max(dates) if dates else None,
        "last_bill": max((b.uid for b in bills), default=None),
    }

def fmt_date(d):
    return f"{d:%Y-%m-%d}" if d else '<span class="empty">—</span>'

def remaining_html(v):
    return '<span class="ok">0 €</span>' if v <= 0.01 else f'<span class="due">{fmt_eur(v)}</span>'

# ─── "Tous" tab ───────────────────────────────────────────────────────────────

projects = sorted(db.projects, key=lambda p: (p.name or p.uid).lower())
stats = {p.uid: project_stats(p) for p in projects}

all_rows = ""
tot = defaultdict(float)
for p in projects:
    s = stats[p.uid]
    client = p.getClient(datetime.now())
    for k in ("worked", "billed", "unbilled", "bills", "ht", "ttc", "received", "remaining"):
        tot[k] += s[k]
    all_rows += f"""<tr>
      <td>{swatch(p.color)}{p.name}</td>
      <td>{client.name if client else '<span class="empty">?</span>'}</td>
      <td class="num">{p.getTaux(datetime.now()) or "—"}&nbsp;€/j</td>
      <td class="num">{fmt_days(s['worked'])}</td>
      <td class="num">{fmt_days(s['billed'])}</td>
      <td class="num">{fmt_days(s['unbilled']) if s['unbilled'] > 0 else '<span class="empty">—</span>'}</td>
      <td class="num">{s['bills']}</td>
      <td class="num">{fmt_eur(s['ht'])}</td>
      <td class="num">{fmt_eur(s['received'])}</td>
      <td class="num">{remaining_html(s['remaining'])}</td>
      <td>{fmt_date(s['last'])}</td>
    </tr>"""

all_rows += f"""<tr class="total-row">
  <td>Total</td><td></td><td></td>
  <td class="num">{fmt_days(tot['worked'])}</td>
  <td class="num">{fmt_days(tot['billed'])}</td>
  <td class="num">{fmt_days(tot['unbilled'])}</td>
  <td class="num">{tot['bills']:g}</td>
  <td class="num">{fmt_eur(tot['ht'])}</td>
  <td class="num">{fmt_eur(tot['received'])}</td>
  <td class="num">{fmt_eur(tot['remaining'])}</td>
  <td></td>
</tr>"""

all_panel = f"""
<div class="cards">
  {card("Projets", str(len(projects)))}
  {card("Total HT facturé", fmt_eur(tot['ht']))}
  {card("Reçu TTC", fmt_eur(tot['received']))}
  {card("Reste à recevoir", fmt_eur(tot['remaining']), "card-due" if tot['remaining'] > 0.01 else "")}
  {card("Jours non facturés", fmt_days(tot['unbilled']), "card-warn" if tot['unbilled'] > 0 else "")}
</div>
<table data-default-sort="0:asc">
  <thead>{th("Projet", "Client actuel", "Taux actuel", "Jours travaillés", "Facturés", "Non facturés", "Factures", "HT facturé", "Reçu TTC", "Reste TTC", "Dernière tâche")}</thead>
  <tbody>{all_rows}</tbody>
</table>"""

# ─── per-project tab ──────────────────────────────────────────────────────────

def history_html(base, dated, fmt):
    """'base' then 'from YYYY-MM-DD: value' lines, oldest first."""
    lines = [fmt(base)] if base is not None else []
    lines += [f'<span class="mono">{dt:%Y-%m-%d}</span> → {fmt(v)}' for dt, v in dated]
    return "<br>".join(lines) if lines else '<span class="empty">—</span>'

def client_label(uid):
    c = db.getClient(uid)
    return c.name if c else f'<span class="empty">{uid} (inconnu)</span>'

def build_project_panel(p):
    s = stats[p.uid]
    client = p.getClient(datetime.now())

    taux_base, taux_dated = _parse_taux_entries(p.assoc.filterKeys("taux"))

    cards_html = f"""<div class="cards">
      {card("Client actuel", client.name if client else "?")}
      {card("Taux actuel", f"{p.getTaux(datetime.now()) or '—'}&nbsp;€/j")}
      {card("Jours travaillés", fmt_days(s['worked']))}
      {card("Facturés", fmt_days(s['billed']))}
      {card("Non facturés", fmt_days(s['unbilled']), "card-warn" if s['unbilled'] > 0 else "")}
      {card("HT facturé", fmt_eur(s['ht']))}
      {card("Reçu TTC", fmt_eur(s['received']))}
      {card("Reste TTC", fmt_eur(s['remaining']), "card-due" if s['remaining'] > 0.01 else "")}
    </div>"""

    info_html = f"""<table class="info-table">
      <tbody>
        <tr><td class="info-label">UID</td><td class="mono">{p.uid}</td></tr>
        <tr><td class="info-label">Client</td><td>{history_html(p.client.uid if p.client else None, p._client_dated, client_label)}</td></tr>
        <tr><td class="info-label">Taux</td><td>{history_html(taux_base, taux_dated, lambda v: f"{v} €/j")}</td></tr>
        <tr><td class="info-label">TVA projet</td><td>{p.assoc.filterKey("tva") or '<span class="empty">—</span>'}</td></tr>
        <tr><td class="info-label">Couleur</td><td>{swatch(p.color)}<span class="mono">{p.color or ""}</span></td></tr>
        <tr><td class="info-label">Première tâche</td><td>{fmt_date(s['first'])}</td></tr>
        <tr><td class="info-label">Dernière tâche</td><td>{fmt_date(s['last'])}</td></tr>
        <tr><td class="info-label">Dernière facture</td><td>{s['last_bill'] or '<span class="empty">—</span>'}</td></tr>
      </tbody>
    </table>"""

    # bills
    bill_rows = ""
    for b in sorted(p.bills or [], key=lambda b: b.uid):
        fuid = b.getFullUid() or b.uid
        pays = paid_by_fuid.get(fuid, [])
        received = sum(pay.amount for pay in pays)
        remaining = b.getTTC() - received
        last_pay = max((pay.date for pay in pays), default=None)
        paid_on = f"{last_pay:%Y-%m-%d}" if remaining <= 0.01 and last_pay else '<span class="empty">—</span>'
        forfait_tag = '<span class="tag forfait">forfait</span>' if b.isForfait() else ""
        bill_rows += f"""<tr{' class="unpaid"' if remaining > 0.01 else ''}>
          <td class="mono">{fuid}</td>
          <td>{b.uid}</td>
          <td>{b.start:%Y-%m-%d}&nbsp;→&nbsp;{b.end:%Y-%m-%d}{forfait_tag}</td>
          <td class="num">{fmt_days(b.countDays())}</td>
          <td class="num">{fmt_eur(b.getHT())}</td>
          <td class="num">{fmt_eur(b.getTTC())}</td>
          <td class="num">{fmt_eur(received)}</td>
          <td class="num">{remaining_html(remaining)}</td>
          <td>{paid_on}</td>
        </tr>"""

    # worked / billed days per year
    billed_ids = {id(t) for b in (p.bills or []) for t in b.tasks}
    by_year = defaultdict(lambda: {"worked": 0.0, "unbilled": 0.0, "ht": 0.0})
    for t in p.tasks or []:
        by_year[t.date.year]["worked"] += t.getTimeSpent()
        if id(t) not in billed_ids:
            by_year[t.date.year]["unbilled"] += t.getTimeSpent()
    for b in p.bills or []:
        by_year[b.getDatetime().year]["ht"] += b.getHT()
    year_rows = "".join(f"""<tr>
          <td>{y}</td>
          <td class="num">{fmt_days(d['worked'])}</td>
          <td class="num">{fmt_days(d['unbilled']) if d['unbilled'] > 0 else '<span class="empty">—</span>'}</td>
          <td class="num">{fmt_eur(d['ht'])}</td>
        </tr>""" for y, d in sorted(by_year.items()))

    return f"""
    {cards_html}
    <div class="two-col">
      <div>
        <h2>Paramètres</h2>
        {info_html}
      </div>
      <div>
        <h2>Par année</h2>
        <table data-default-sort="0:desc">
          <thead>{th("Année", "Jours travaillés", "Non facturés", "HT facturé")}</thead>
          <tbody>{year_rows or '<tr><td colspan="4" class="empty">Aucune donnée</td></tr>'}</tbody>
        </table>
      </div>
    </div>
    <h2>Factures</h2>
    <table data-default-sort="1:desc">
      <thead>{th("ID", "Date facture", "Période", "Jours", "HT", "TTC", "Reçu", "Reste", "Payée le")}</thead>
      <tbody>{bill_rows or '<tr><td colspan="9" class="empty">Aucune facture</td></tr>'}</tbody>
    </table>"""

# ─── build tabs ───────────────────────────────────────────────────────────────

tabs_nav = '<button class="tab-btn active" onclick="showTab(\'tab-all\')" id="btn-tab-all">Tous</button>'
tabs_content = f'<div class="tab-panel active" id="tab-all">{all_panel}</div>'

for p in projects:
    tid = f"tab-{p.uid}"
    tabs_nav     += f'<button class="tab-btn" onclick="showTab(\'{tid}\')" id="btn-{tid}">{swatch(p.color)}{p.name}</button>'
    tabs_content += f'<div class="tab-panel" id="{tid}">{build_project_panel(p)}</div>'

# ─── assemble ─────────────────────────────────────────────────────────────────

generated_at = datetime.now().strftime("%Y-%m-%d %H:%M")

page_style = """
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { font-family: system-ui, sans-serif; font-size: 14px; background: #f5f5f5; color: #222; }
  h1 { font-size: 20px; font-weight: 700; margin-bottom: 4px; }
  .meta { color: #888; font-size: 12px; margin-bottom: 24px; }
  h2 { font-size: 11px; font-weight: 600; text-transform: uppercase; letter-spacing: .06em;
        color: #999; margin: 28px 0 10px; }

  /* tabs */
  .tabs-nav { display: flex; flex-wrap: wrap; gap: 6px; margin-bottom: 24px; }
  .tab-btn { padding: 7px 16px; border: 1px solid #ddd; border-radius: 20px;
              background: #fff; cursor: pointer; font-size: 13px; font-weight: 500;
              color: #555; transition: background .15s, color .15s;
              display: inline-flex; align-items: center; }
  .tab-btn:hover { background: #f0f0f0; }
  .tab-btn.active { background: #222; color: #fff; border-color: #222; }
  .tab-panel { display: none; }
  .tab-panel.active { display: block; }

  /* cards */
  .cards { display: flex; gap: 12px; flex-wrap: wrap; margin-bottom: 24px; }
  .card { background: #fff; border-radius: 8px; padding: 14px 20px; min-width: 130px;
            box-shadow: 0 1px 3px rgba(0,0,0,.07); }
  .card-label { font-size: 10px; color: #aaa; text-transform: uppercase; letter-spacing: .05em; }
  .card-value { font-size: 20px; font-weight: 700; margin-top: 4px; }
  .card-due .card-value { color: #c62828; }
  .card-warn .card-value { color: #b06000; }

  /* tables */
  table { width: 100%; border-collapse: collapse; background: #fff; border-radius: 8px;
            overflow: hidden; box-shadow: 0 1px 3px rgba(0,0,0,.07); margin-bottom: 4px; }
  th { background: #f0f0f0; text-align: left; padding: 7px 12px;
        font-size: 10px; text-transform: uppercase; letter-spacing: .05em; color: #888; }
  td { padding: 7px 12px; border-top: 1px solid #f0f0f0; vertical-align: middle; }
  tr:hover td { background: #fafafa; }
  .num { text-align: left; font-variant-numeric: tabular-nums; white-space: nowrap; }
  .mono { font-family: monospace; font-size: 12px; color: #777; }
  .empty { color: #bbb; font-style: italic; }
  .ok  { color: #2e7d32; font-weight: 600; }
  .due { color: #c62828; font-weight: 600; }
  .total-row td { font-weight: 600; background: #f7f7f7; border-top: 2px solid #e0e0e0; }
  tr.unpaid td { background: #fffaf0; }
  .tag { font-size: 10px; border-radius: 4px; padding: 2px 6px; margin-left: 6px; white-space: nowrap; }
  .tag.forfait { background: #fce8b2; color: #b06000; }

  .info-table .info-label { width: 140px; color: #888; font-size: 12px; }
  .info-table td { vertical-align: top; }

  .swatch { display: inline-block; width: 10px; height: 10px; border-radius: 50%;
             margin-right: 7px; flex-shrink: 0; vertical-align: middle;
             border: 1px solid rgba(0,0,0,.1); }
  .swatch.none { background: transparent; border-style: dashed; }

  .two-col { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }
  @media (max-width: 900px) { .two-col { grid-template-columns: 1fr; } }
"""

body_content = f"""
<h1>Projets</h1>
<div class="meta">Généré le {generated_at} · {len(projects)} projets — modifiables dans database/projects/{{uid}}.proj</div>

<div class="tabs-nav">{tabs_nav}</div>

{tabs_content}

<script>
function showTab(id) {{
  document.querySelectorAll('.tab-panel').forEach(el => el.classList.remove('active'));
  document.querySelectorAll('.tab-btn').forEach(el => el.classList.remove('active'));
  document.getElementById(id).classList.add('active');
  document.getElementById('btn-' + id).classList.add('active');
}}
</script>
"""

html = render_shell("Projets", "projects.html", body_content, page_style)

# ─── write ────────────────────────────────────────────────────────────────────

out_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "exports", "view"))
os.makedirs(out_dir, exist_ok=True)
out_path = os.path.join(out_dir, "projects.html")

with open(out_path, "w", encoding="utf-8") as f:
    f.write(html)

print(f"\n── projects ──")
for p in projects:
    s = stats[p.uid]
    print(f"  {p.uid:<20} travaillés:{s['worked']:>6.1f}j  facturés:{s['billed']:>6.1f}j  non-facturés:{s['unbilled']:>5.1f}j  HT:{s['ht']:>10.2f}  reste:{s['remaining']:>9.2f}")
print(f"\nview @ {out_path}")

if hasattr(os, "startfile") and not configs.webview_mode:
    os.startfile(os.path.normpath(out_path))

if configs.pause_on_exit and not configs.webview_mode: input("\nEntrée pour fermer...")
