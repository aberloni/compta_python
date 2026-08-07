"""
Generate exports/view/tva.html

TVA à déclarer par mois : une facture n'est due en TVA que lorsque son
paiement a été reçu (encaissements). On croise donc les factures avec les
virements du wiring pour répartir la TVA de chaque facture sur le(s) mois
où son paiement a effectivement été reçu (au prorata en cas de paiement partiel).

2 tables:
  1. TVA par mois (à déclarer)
  2. Détail des encaissements (facture -> virement -> part de TVA)
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
from datetime import datetime
from collections import defaultdict

import configs
from packages.database.database import Database
from packages.database.wiring import Wiring

# ─── load ─────────────────────────────────────────────────────────────────────

db = Database.init_billing()
wiring = Wiring()

known_uids  = {c.uid for c in db.clients}
known_wires = [w for w in wiring.wires if w.client_uid in known_uids]

# paid_by_fuid[fuid] = list of wires that reference it
paid_by_fuid = defaultdict(list)
for w in known_wires:
    if w.bill_fuid:
        paid_by_fuid[w.bill_fuid].append(w)

all_bills = []
for p in db.projects:
    for b in p.bills:
        all_bills.append((p, b))
all_bills.sort(key=lambda x: x[1].uid)

# ─── helpers ──────────────────────────────────────────────────────────────────

def fmt(v):
    return f"{v:,.2f}".replace(",", " ") + " €"

def th(*cols):
    return "<tr>" + "".join(f"<th>{c}</th>" for c in cols) + "</tr>"

def card(label, value, cls=""):
    return f'<div class="card {cls}"><div class="card-label">{label}</div><div class="card-value">{value}</div></div>'

# ─── une facture payée intégralement compte pour son mois de finalisation ─────
# une facture impayée (ou partiellement payée) est ignorée : la TVA n'est due
# qu'une fois le paiement finalisé, et elle est assignée au mois du virement
# qui complète ce paiement.

by_month = defaultdict(lambda: {"ht": 0.0, "tva": 0.0, "ttc": 0.0})
details  = []  # (wire_date, month, client_name, fuid, project_name, ht, tva, ttc)

for p, b in all_bills:
    client = b.getClient()
    if not client:
        continue

    ttc = b.getTTC()
    if ttc <= 0.01:
        continue

    fuid = b.getFullUid() or b.uid
    wires = paid_by_fuid.get(fuid, [])
    if not wires:
        continue

    received = sum(w.amount for w in wires)
    if received + 0.01 < ttc:
        continue  # pas encore payée intégralement -> pas de TVA due

    final_wire = max(wires, key=lambda w: w.date)
    month = final_wire.date.strftime("%Y-%m")
    ht = b.getHT()
    tva = b.getTvaTotal()

    by_month[month]["ht"]  += ht
    by_month[month]["tva"] += tva
    by_month[month]["ttc"] += ttc

    details.append((final_wire.date, month, client.name, fuid, p.name, ht, tva, ttc))

details.sort(key=lambda d: d[0])

# ─── table 1 : TVA par mois ────────────────────────────────────────────────────

def _all_months(months):
    """Yield 'YYYY-MM' for every month between the earliest and latest, inclusive."""
    pairs = [tuple(int(x) for x in m.split("-")) for m in months]
    start_y, start_m = min(pairs)
    end_y, end_m = max(pairs)
    y, mo = start_y, start_m
    while (y, mo) <= (end_y, end_m):
        yield f"{y:04d}-{mo:02d}"
        mo += 1
        if mo > 12:
            mo = 1
            y += 1

month_rows = ""
total_ht = total_tva = total_ttc = 0.0
for m in _all_months(by_month.keys()) if by_month else []:
    d = by_month.get(m, {"ht": 0.0, "tva": 0.0, "ttc": 0.0})
    total_ht  += d["ht"]
    total_tva += d["tva"]
    total_ttc += d["ttc"]
    empty_cls = " empty-month" if m not in by_month else ""
    month_rows += f"""<tr class="{empty_cls}">
      <td>{m}</td>
      <td class="num">{fmt(d['ht'])}</td>
      <td class="num tva">{fmt(d['tva'])}</td>
      <td class="num">{fmt(d['ttc'])}</td>
    </tr>"""

if month_rows:
    month_rows += f"""<tr class="total-row">
      <td>Total</td>
      <td class="num">{fmt(total_ht)}</td>
      <td class="num tva">{fmt(total_tva)}</td>
      <td class="num">{fmt(total_ttc)}</td>
    </tr>"""

# ─── table 2 : détail des encaissements ────────────────────────────────────────

detail_rows = ""
for w_date, month, client_name, fuid, project_name, ht, tva, ttc in details:
    detail_rows += f"""<tr>
      <td>{w_date:%Y-%m-%d}</td>
      <td>{month}</td>
      <td class="mono">{fuid}</td>
      <td>{client_name}</td>
      <td>{project_name}</td>
      <td class="num">{fmt(ht)}</td>
      <td class="num tva">{fmt(tva)}</td>
      <td class="num">{fmt(ttc)}</td>
    </tr>"""

# ─── summary cards ────────────────────────────────────────────────────────────

summary = f"""<div class="cards">
  {card("HT encaissé", fmt(total_ht))}
  {card("TVA à déclarer", fmt(total_tva), "card-due")}
  {card("TTC encaissé", fmt(total_ttc))}
</div>"""

# ─── assemble ─────────────────────────────────────────────────────────────────

generated_at = datetime.now().strftime("%Y-%m-%d %H:%M")

html = f"""<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8"/>
<title>TVA view</title>
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ font-family: system-ui, sans-serif; font-size: 14px; background: #f5f5f5; color: #222; padding: 32px; }}
  h1 {{ font-size: 20px; font-weight: 700; margin-bottom: 4px; }}
  .meta {{ color: #888; font-size: 12px; margin-bottom: 24px; }}
  h2 {{ font-size: 11px; font-weight: 600; text-transform: uppercase; letter-spacing: .06em;
        color: #999; margin: 32px 0 10px; }}

  .cards {{ display: flex; gap: 12px; flex-wrap: wrap; margin-bottom: 28px; }}
  .card {{ background: #fff; border-radius: 8px; padding: 14px 20px; min-width: 140px;
            box-shadow: 0 1px 3px rgba(0,0,0,.07); }}
  .card-label {{ font-size: 10px; color: #aaa; text-transform: uppercase; letter-spacing: .05em; }}
  .card-value {{ font-size: 20px; font-weight: 700; margin-top: 4px; }}
  .card-due .card-value {{ color: #c62828; }}

  table {{ width: 100%; border-collapse: collapse; background: #fff; border-radius: 8px;
            overflow: hidden; box-shadow: 0 1px 3px rgba(0,0,0,.07); margin-bottom: 4px; }}
  th {{ background: #f0f0f0; text-align: left; padding: 7px 12px;
        font-size: 10px; text-transform: uppercase; letter-spacing: .05em; color: #888; }}
  td {{ padding: 7px 12px; border-top: 1px solid #f0f0f0; vertical-align: middle; }}
  tr:hover td {{ background: #fafafa; }}
  .num {{ text-align: right; font-variant-numeric: tabular-nums; white-space: nowrap; }}
  .mono {{ font-family: monospace; font-size: 12px; color: #777; }}
  .tva {{ color: #c62828; font-weight: 600; }}
  .empty-month td {{ color: #ccc; }}
  .empty-month .tva {{ color: #ddd; }}
  .total-row td {{ font-weight: 600; background: #f7f7f7; border-top: 2px solid #e0e0e0; }}
  .empty {{ color: #bbb; font-style: italic; }}
</style>
</head>
<body>

<h1>TVA à déclarer</h1>
<div class="meta">Généré le {generated_at} · basé sur les encaissements (paiements reçus)</div>

{summary}

<h2>Par mois</h2>
<table>
  <thead>{th("Mois", "HT", "TVA", "TTC")}</thead>
  <tbody>{month_rows or '<tr><td colspan="4" class="empty">Aucun encaissement</td></tr>'}</tbody>
</table>

<h2>Détail des encaissements</h2>
<table>
  <thead>{th("Date virement", "Mois", "Facture", "Client", "Projet", "HT", "TVA", "TTC")}</thead>
  <tbody>{detail_rows or '<tr><td colspan="8" class="empty">Aucun encaissement</td></tr>'}</tbody>
</table>

</body>
</html>"""

# ─── write ────────────────────────────────────────────────────────────────────

out_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "exports", "view"))
os.makedirs(out_dir, exist_ok=True)
out_path = os.path.join(out_dir, "tva.html")

with open(out_path, "w", encoding="utf-8") as f:
    f.write(html)

print(f"\n── tva ──")
for m in sorted(by_month):
    d = by_month[m]
    print(f"{m} >> HT : {d['ht']:g} | TVA : {d['tva']:g} | TTC : {d['ttc']:g}")
print(f"\nTotal TVA à déclarer : {total_tva:.2f} €")
print(f"view @ {out_path}")

if hasattr(os, "startfile"):
    os.startfile(os.path.normpath(out_path))

if configs.pause_on_exit: input("\nEntrée pour fermer...")
