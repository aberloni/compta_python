"""
Generate exports/view/billing.html — a billing analysis dashboard.

Tabs: one per year with bills + all time.
Each tab shows: summary cards, bills table, by-month, by-client, by-project.
"""

import locale
import sys
import traceback

import configs

def _excepthook(etype, value, tb):
    traceback.print_exception(etype, value, tb)
    if configs.pause_on_exit: input("\nEntrée pour fermer...")
sys.excepthook = _excepthook

try:
    locale.setlocale(locale.LC_ALL, 'fr_FR')
except locale.Error:
    locale.setlocale(locale.LC_ALL, '')

import os
from datetime import datetime, date
from dateutil.relativedelta import relativedelta
from collections import defaultdict

import configs
from packages.database.database import Database
from packages.database.wiring import Wiring
from modules.path import Path

# ─── load ─────────────────────────────────────────────────────────────────────

db = Database.init_billing()
wiring = Wiring()

all_bills = []
for p in db.projects:
    for b in p.bills:
        all_bills.append((p, b))

all_bills.sort(key=lambda x: x[1].uid)

# ─── helpers ──────────────────────────────────────────────────────────────────

def fmt_eur(v):
    return f"{v:,.2f}&nbsp;€".replace(",", " ")

def fmt_days(v):
    return f"{v:g}&nbsp;j"

def card(label, value):
    return f'<div class="card"><div class="card-label">{label}</div><div class="card-value">{value}</div></div>'

def th(*cols):
    return "<tr>" + "".join(f"<th>{c}</th>" for c in cols) + "</tr>"

# ─── per-tab rendering ────────────────────────────────────────────────────────

def render_tab(bills_slice):
    """Build the inner HTML for one time-range tab."""

    total_ht = total_tva = total_ttc = total_days = 0.0
    by_month   = defaultdict(lambda: {"ht": 0.0, "ttc": 0.0, "days": 0.0})
    by_client  = defaultdict(lambda: {"name": "", "ht": 0.0, "ttc": 0.0, "days": 0.0, "bills": 0})
    by_project = defaultdict(lambda: {"name": "", "client": "", "ht": 0.0, "ttc": 0.0, "days": 0.0, "bills": 0})

    for p, b in bills_slice:
        ht    = b.getHT()
        tva   = b.getTvaTotal()
        ttc   = b.getTTC()
        days  = b.countDays()
        client = b.getClient()
        month  = b.uid[:7]

        total_ht   += ht
        total_tva  += tva
        total_ttc  += ttc
        total_days += days

        by_month[month]["ht"]   += ht
        by_month[month]["ttc"]  += ttc
        by_month[month]["days"] += days

        cuid = client.uid if client else "?"
        by_client[cuid]["name"]  = client.name if client else cuid
        by_client[cuid]["ht"]   += ht
        by_client[cuid]["ttc"]  += ttc
        by_client[cuid]["days"] += days
        by_client[cuid]["bills"] += 1

        by_project[p.uid]["name"]   = p.name
        by_project[p.uid]["client"] = client.name if client else "?"
        by_project[p.uid]["ht"]    += ht
        by_project[p.uid]["ttc"]   += ttc
        by_project[p.uid]["days"]  += days
        by_project[p.uid]["bills"] += 1

    # cards
    cards_html = f"""<div class="cards">
      {card("Total HT", fmt_eur(total_ht))}
      {card("TVA", fmt_eur(total_tva))}
      {card("Total TTC", fmt_eur(total_ttc))}
      {card("Jours facturés", fmt_days(total_days))}
      {card("Factures", str(len(bills_slice)))}
    </div>"""

    # bills table
    bills_rows = ""
    for p, b in bills_slice:
        client = b.getClient()
        fuid = b.getFullUid() or b.uid
        taux_range = p.getTauxRange(b.start, b.end)
        taux_str = " → ".join(str(t) for t in taux_range) + " €/j"
        frais_tag = f'<span class="tag">+frais {fmt_eur(b.getTransactionsTTC())}</span>' if b.hasTransactions() else ""
        forfait_tag = '<span class="tag forfait">forfait</span>' if b.isForfait() else ""
        bills_rows += f"""<tr>
          <td class="mono">{fuid}</td>
          <td>{b.uid}</td>
          <td>{b.start:%Y-%m-%d}&nbsp;→&nbsp;{b.end:%Y-%m-%d}</td>
          <td>{client.name if client else "?"}</td>
          <td>{p.name}{forfait_tag}</td>
          <td class="num">{fmt_days(b.countDays())}</td>
          <td class="num">{taux_str}</td>
          <td class="num">{fmt_eur(b.getHT())}</td>
          <td class="num">{fmt_eur(b.getTTC())}{frais_tag}</td>
        </tr>"""

    # by month
    month_rows = ""
    for m in sorted(by_month):
        d = by_month[m]
        month_rows += f"""<tr>
          <td>{m}</td>
          <td class="num">{fmt_days(d['days'])}</td>
          <td class="num">{fmt_eur(d['ht'])}</td>
          <td class="num">{fmt_eur(d['ttc'])}</td>
        </tr>"""

    # by client
    client_rows = ""
    for uid, d in sorted(by_client.items(), key=lambda x: -x[1]["ht"]):
        client_rows += f"""<tr>
          <td>{d['name']}</td>
          <td class="num">{d['bills']}</td>
          <td class="num">{fmt_days(d['days'])}</td>
          <td class="num">{fmt_eur(d['ht'])}</td>
          <td class="num">{fmt_eur(d['ttc'])}</td>
        </tr>"""

    # by project
    project_rows = ""
    for uid, d in sorted(by_project.items(), key=lambda x: -x[1]["ht"]):
        project_rows += f"""<tr>
          <td>{d['name']}</td>
          <td>{d['client']}</td>
          <td class="num">{d['bills']}</td>
          <td class="num">{fmt_days(d['days'])}</td>
          <td class="num">{fmt_eur(d['ht'])}</td>
          <td class="num">{fmt_eur(d['ttc'])}</td>
        </tr>"""

    # paiements
    received_by_client = wiring.by_client()
    payment_rows = ""
    total_facture = total_recu = 0.0
    for uid, d in sorted(by_client.items(), key=lambda x: -x[1]["ttc"]):
        facture = d["ttc"]
        recu = received_by_client.get(uid, 0.0)
        reste = facture - recu
        total_facture += facture
        total_recu += recu
        reste_html = f'<span class="reste-ok">0 €</span>' if reste <= 0.01 else f'<span class="reste-due">{fmt_eur(reste)}</span>'
        payment_rows += f"""<tr>
          <td>{d['name']}</td>
          <td class="num">{fmt_eur(facture)}</td>
          <td class="num">{fmt_eur(recu)}</td>
          <td class="num">{reste_html}</td>
        </tr>"""
    total_reste = total_facture - total_recu
    payment_rows += f"""<tr class="total-row">
      <td>Total</td>
      <td class="num">{fmt_eur(total_facture)}</td>
      <td class="num">{fmt_eur(total_recu)}</td>
      <td class="num">{fmt_eur(total_reste)}</td>
    </tr>"""

    payment_html = f"""
    <h2>Paiements reçus</h2>
    <table>
      <thead>{th("Client", "Facturé TTC", "Reçu TTC", "Reste à recevoir")}</thead>
      <tbody>{payment_rows}</tbody>
    </table>"""

    # pie chart (SVG) — TTC par client
    COLORS = ["#4e79a7","#f28e2b","#e15759","#76b7b2","#59a14f",
              "#edc948","#b07aa1","#ff9da7","#9c755f","#bab0ac"]
    import math
    pie_svg = ""
    if total_ttc > 0:
        cx, cy, r = 110, 110, 90
        sorted_clients = sorted(by_client.items(), key=lambda x: -x[1]["ttc"])
        angle = -math.pi / 2
        slices = ""
        legend = ""
        for idx, (cuid, cd) in enumerate(sorted_clients):
            frac = cd["ttc"] / total_ttc
            sweep = frac * 2 * math.pi
            x1 = cx + r * math.cos(angle)
            y1 = cy + r * math.sin(angle)
            x2 = cx + r * math.cos(angle + sweep)
            y2 = cy + r * math.sin(angle + sweep)
            large = 1 if sweep > math.pi else 0
            color = COLORS[idx % len(COLORS)]
            slices += f'<path d="M{cx},{cy} L{x1:.2f},{y1:.2f} A{r},{r} 0 {large},1 {x2:.2f},{y2:.2f} Z" fill="{color}" stroke="#fff" stroke-width="1.5"/>'
            pct = frac * 100
            legend += f'<div class="pie-legend-item"><span class="pie-dot" style="background:{color}"></span>{cd["name"]} — {pct:.1f}%</div>'
            angle += sweep
        pie_svg = f"""
        <div class="pie-wrap">
          <svg width="220" height="220" viewBox="0 0 220 220">{slices}</svg>
          <div class="pie-legend">{legend}</div>
        </div>"""

    return f"""
    {cards_html}

    {payment_html}

    <h2>Factures</h2>
    <table>
      <thead>{th("ID", "Date facture", "Période", "Client", "Projet", "Jours", "Taux", "HT", "TTC")}</thead>
      <tbody>{bills_rows or '<tr><td colspan="9" class="empty">Aucune facture</td></tr>'}</tbody>
    </table>

    <h2>Par mois</h2>
    <table>
      <thead>{th("Mois", "Jours", "HT", "TTC")}</thead>
      <tbody>{month_rows or '<tr><td colspan="4" class="empty">—</td></tr>'}</tbody>
    </table>

    <div class="two-col">
      <div>
        <h2>Par client</h2>
        {pie_svg}
        <table>
          <thead>{th("Client", "Factures", "Jours", "HT", "TTC")}</thead>
          <tbody>{client_rows or '<tr><td colspan="5" class="empty">—</td></tr>'}</tbody>
        </table>
      </div>
      <div>
        <h2>Par projet</h2>
        <table>
          <thead>{th("Projet", "Client", "Factures", "Jours", "HT", "TTC")}</thead>
          <tbody>{project_rows or '<tr><td colspan="6" class="empty">—</td></tr>'}</tbody>
        </table>
      </div>
    </div>
    """

# ─── build tabs ───────────────────────────────────────────────────────────────

# one tab per year with bills, plus "Tout"
years_with_bills = sorted({b.uid[:4] for _, b in all_bills}, reverse=True)

tabs_nav = ""
tabs_content = ""

for i, year in enumerate(years_with_bills):
    tid = f"tab-{year}"
    active = "active" if i == 0 else ""
    slice_ = [(p, b) for p, b in all_bills if b.uid[:4] == year]
    tabs_nav     += f'<button class="tab-btn {active}" onclick="showTab(\'{tid}\')" id="btn-{tid}">{year}</button>'
    tabs_content += f'<div class="tab-panel {active}" id="{tid}">{render_tab(slice_)}</div>'

# "Tout" tab
tid = "tab-all"
tabs_nav     += f'<button class="tab-btn" onclick="showTab(\'{tid}\')" id="btn-{tid}">Tout</button>'
tabs_content += f'<div class="tab-panel" id="{tid}">{render_tab(all_bills)}</div>'

# ─── unbilled tasks ───────────────────────────────────────────────────────────

# collect all task dates covered by at least one bill per project
unbilled_rows = ""
total_unbilled_days = 0.0

for p in db.projects:
    billed_task_ids = set()
    for b in p.bills:
        for t in b.tasks:
            billed_task_ids.add(id(t))

    unbilled = [t for t in p.tasks if id(t) not in billed_task_ids]
    if not unbilled:
        continue

    unbilled.sort(key=lambda t: t.date)
    days = sum(t.getTimeSpent() for t in unbilled)
    total_unbilled_days += days

    taux = p.getTaux(unbilled[-1].date)  # taux at latest unbilled task
    estimated_ht = days * taux

    months_str = ", ".join(sorted({t.date.strftime("%Y-%m") for t in unbilled}))
    client = p.getClient()

    unbilled_rows += f"""<tr>
      <td>{p.name}</td>
      <td>{client.name if client else "?"}</td>
      <td class="num">{fmt_days(days)}</td>
      <td>{months_str}</td>
      <td class="num">{taux}&nbsp;€/j</td>
      <td class="num est">{fmt_eur(estimated_ht)}</td>
    </tr>"""

total_billed_days = sum(b.countDays() for _, b in all_bills)
unbilled_cards = f"""<div class="cards unbilled-cards">
  {card("Jours facturés", fmt_days(total_billed_days))}
  {card("Jours non facturés", fmt_days(total_unbilled_days))}
</div>"""

unbilled_section = f"""
<h2 class="unbilled-title">Jours non facturés</h2>
{unbilled_cards}
<table>
  <thead>{th("Projet", "Client", "Jours", "Mois", "Taux", "Estimé HT")}</thead>
  <tbody>{unbilled_rows or '<tr><td colspan="6" class="empty">Tout est facturé ✓</td></tr>'}</tbody>
</table>""" if unbilled_rows else f"""
<h2 class="unbilled-title">Jours non facturés</h2>
{unbilled_cards}
<p class="all-billed">Tout est facturé ✓</p>"""

# ─── assemble ─────────────────────────────────────────────────────────────────

generated_at = datetime.now().strftime("%Y-%m-%d %H:%M")

html = f"""<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8"/>
<title>Billing view</title>
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ font-family: system-ui, sans-serif; font-size: 14px; background: #f5f5f5; color: #222; padding: 32px; }}
  h1 {{ font-size: 20px; font-weight: 700; margin-bottom: 4px; }}
  .meta {{ color: #888; font-size: 12px; margin-bottom: 24px; }}
  h2 {{ font-size: 12px; font-weight: 600; text-transform: uppercase; letter-spacing: .06em;
        color: #999; margin: 28px 0 10px; }}

  /* tabs */
  .tabs {{ display: flex; gap: 4px; margin-bottom: 24px; }}
  .tab-btn {{ background: #e8e8e8; border: none; border-radius: 6px; padding: 7px 16px;
              font-size: 13px; cursor: pointer; color: #555; font-family: inherit; }}
  .tab-btn:hover {{ background: #ddd; }}
  .tab-btn.active {{ background: #222; color: #fff; }}
  .tab-panel {{ display: none; }}
  .tab-panel.active {{ display: block; }}

  /* cards */
  .cards {{ display: flex; gap: 12px; flex-wrap: wrap; margin-bottom: 4px; }}
  .card {{ background: #fff; border-radius: 8px; padding: 14px 20px; min-width: 140px;
            box-shadow: 0 1px 3px rgba(0,0,0,.07); }}
  .card-label {{ font-size: 10px; color: #aaa; text-transform: uppercase; letter-spacing: .05em; }}
  .card-value {{ font-size: 20px; font-weight: 700; margin-top: 4px; }}

  /* tables */
  table {{ width: 100%; border-collapse: collapse; background: #fff;
            border-radius: 8px; overflow: hidden;
            box-shadow: 0 1px 3px rgba(0,0,0,.07); margin-bottom: 4px; }}
  th {{ background: #f0f0f0; text-align: left; padding: 7px 12px;
        font-size: 10px; text-transform: uppercase; letter-spacing: .05em; color: #888; }}
  td {{ padding: 7px 12px; border-top: 1px solid #f0f0f0; vertical-align: middle; }}
  tr:hover td {{ background: #fafafa; }}
  .num {{ text-align: right; font-variant-numeric: tabular-nums; white-space: nowrap; }}
  .mono {{ font-family: monospace; font-size: 12px; color: #777; }}
  .empty {{ color: #bbb; font-style: italic; }}
  .tag {{ font-size: 10px; background: #e8f0fe; color: #3367d6;
          border-radius: 4px; padding: 2px 6px; margin-left: 4px; white-space: nowrap; }}
  .tag.forfait {{ background: #fce8b2; color: #b06000; }}
  .reste-ok  {{ color: #2e7d32; font-weight: 600; }}
  .reste-due {{ color: #c62828; font-weight: 600; }}
  .total-row td {{ font-weight: 600; background: #f7f7f7; border-top: 2px solid #e0e0e0; }}

  /* two-col layout for client + project side by side */
  .two-col {{ display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }}
  @media (max-width: 900px) {{ .two-col {{ grid-template-columns: 1fr; }} }}

  /* pie chart */
  .pie-wrap {{ display: flex; align-items: center; gap: 20px; margin-bottom: 16px; }}
  .pie-legend {{ display: flex; flex-direction: column; gap: 6px; font-size: 13px; }}
  .pie-legend-item {{ display: flex; align-items: center; gap: 8px; }}
  .pie-dot {{ display: inline-block; width: 12px; height: 12px; border-radius: 50%; flex-shrink: 0; }}

  /* unbilled section */
  .unbilled-title {{ color: #b06000; margin-top: 40px; border-top: 2px solid #fce8b2; padding-top: 20px; }}
  .unbilled-cards .card:last-child .card-value {{ color: #b06000; }}
  .est {{ color: #b06000; font-weight: 600; }}
  .all-billed {{ color: #2e7d32; font-size: 13px; margin-top: 8px; }}
</style>
</head>
<body>

<h1>Billing view</h1>
<div class="meta">Généré le {generated_at} · {len(all_bills)} factures au total</div>

<div class="tabs">{tabs_nav}</div>

{tabs_content}

{unbilled_section}

<script>
function showTab(id) {{
  document.querySelectorAll('.tab-panel').forEach(el => el.classList.remove('active'));
  document.querySelectorAll('.tab-btn').forEach(el => el.classList.remove('active'));
  document.getElementById(id).classList.add('active');
  document.getElementById('btn-' + id).classList.add('active');
}}
</script>
</body>
</html>"""

# ─── write ────────────────────────────────────────────────────────────────────

out_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "exports", "view"))
os.makedirs(out_dir, exist_ok=True)
out_path = os.path.join(out_dir, "billing.html")

with open(out_path, "w", encoding="utf-8") as f:
    f.write(html)

print(f"\n── billing ──")
print(f"projets      : {len(db.projects)}")
print(f"factures     : {len(all_bills)}")
for p in db.projects:
    billed   = sum(b.countDays() for b in p.bills)
    unbilled = sum(t.getTimeSpent() for t in p.tasks if not any(t in b.tasks for b in p.bills))
    print(f"  {p.uid:<20} tâches:{len(p.tasks):>3}  facturés:{billed:>5.1f}j  non-facturés:{unbilled:>5.1f}j")
print(f"\nview @ {out_path}")

if hasattr(os, "startfile"):
    os.startfile(os.path.normpath(out_path))

if configs.pause_on_exit: input("\nEntrée pour fermer...")
