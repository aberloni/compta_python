"""
Generate exports/view/trimester.html

Charges sociales (cotisations + CFP + versement libératoire) dues par trimestre.
Une facture n'est due qu'une fois son paiement reçu intégralement (encaissement) ;
elle compte pour le trimestre du virement qui finalise ce paiement. Les taux
appliqués sont ceux en vigueur à la date de ce virement (voir database/infos/impots.info).

T1 = jan-mar, T2 = avr-jun, T3 = jul-sep, T4 = oct-dec.

2 tables:
  1. Charges par trimestre (à payer)
  2. Détail des encaissements (facture -> virement -> trimestre)
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
from packages.database.impots import Impots

# ─── load ─────────────────────────────────────────────────────────────────────

db = Database.init_billing()
wiring = Wiring()
impots = Impots()

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

def to_trimester(date):
    """Return 'YYYY-Tn' for a datetime (T1=jan-mar, T2=avr-jun, T3=jul-sep, T4=oct-dec)."""
    q = (date.month - 1) // 3 + 1
    return f"{date.year}-T{q}"

# ─── une facture payée intégralement compte pour son trimestre de finalisation ─
# une facture impayée (ou partiellement payée) est ignorée : les cotisations ne sont
# dues qu'une fois le paiement finalisé, et assignées au trimestre du virement qui
# complète ce paiement. Le taux appliqué est celui en vigueur à la date de ce virement.

by_trim  = defaultdict(lambda: {"ht": 0.0, "cotisations": 0.0, "cfp": 0.0, "liberatoire": 0.0, "total": 0.0})
details  = []  # (wire_date, trimester, client_name, fuid, project_name, ht, cotisations, cfp, liberatoire, total)

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
        continue  # pas encore payée intégralement -> pas de charges dues

    final_wire = max(wires, key=lambda w: w.date)
    trim = to_trimester(final_wire.date)
    ht = b.getHT()

    cotisations = ht * impots.getCotisations(final_wire.date)
    cfp         = ht * impots.getCfp(final_wire.date)
    liberatoire = ht * impots.getLiberatoire(final_wire.date)
    total       = cotisations + cfp + liberatoire

    by_trim[trim]["ht"]          += ht
    by_trim[trim]["cotisations"] += cotisations
    by_trim[trim]["cfp"]         += cfp
    by_trim[trim]["liberatoire"] += liberatoire
    by_trim[trim]["total"]       += total

    details.append((final_wire.date, trim, client.name, fuid, p.name, ht, cotisations, cfp, liberatoire, total))

details.sort(key=lambda d: d[0])

# ─── table 1 : charges par trimestre ───────────────────────────────────────────

def _all_trimesters(trims):
    """Yield 'YYYY-Tn' for every trimester between the earliest and latest, inclusive."""
    pairs = [(int(t.split("-T")[0]), int(t.split("-T")[1])) for t in trims]
    start_y, start_q = min(pairs)
    end_y, end_q = max(pairs)
    y, q = start_y, start_q
    while (y, q) <= (end_y, end_q):
        yield f"{y}-T{q}"
        q += 1
        if q > 4:
            q = 1
            y += 1

_empty_trim = {"ht": 0.0, "cotisations": 0.0, "cfp": 0.0, "liberatoire": 0.0, "total": 0.0}

trim_rows = ""
total_ht = total_cotisations = total_cfp = total_liberatoire = total_charges = 0.0
for t in _all_trimesters(by_trim.keys()) if by_trim else []:
    d = by_trim.get(t, _empty_trim)
    total_ht          += d["ht"]
    total_cotisations += d["cotisations"]
    total_cfp         += d["cfp"]
    total_liberatoire += d["liberatoire"]
    total_charges     += d["total"]
    empty_cls = " empty-trim" if t not in by_trim else ""
    trim_rows += f"""<tr class="{empty_cls}">
      <td>{t}</td>
      <td class="num">{fmt(d['ht'])}</td>
      <td class="num">{fmt(d['cotisations'])}</td>
      <td class="num">{fmt(d['cfp'])}</td>
      <td class="num">{fmt(d['liberatoire'])}</td>
      <td class="num charges">{fmt(d['total'])}</td>
    </tr>"""

if trim_rows:
    trim_rows += f"""<tr class="total-row">
      <td>Total</td>
      <td class="num">{fmt(total_ht)}</td>
      <td class="num">{fmt(total_cotisations)}</td>
      <td class="num">{fmt(total_cfp)}</td>
      <td class="num">{fmt(total_liberatoire)}</td>
      <td class="num charges">{fmt(total_charges)}</td>
    </tr>"""

# ─── table 2 : détail des encaissements ────────────────────────────────────────

detail_rows = ""
for w_date, trim, client_name, fuid, project_name, ht, cotisations, cfp, liberatoire, total in details:
    detail_rows += f"""<tr>
      <td>{w_date:%Y-%m-%d}</td>
      <td>{trim}</td>
      <td class="mono">{fuid}</td>
      <td>{client_name}</td>
      <td>{project_name}</td>
      <td class="num">{fmt(ht)}</td>
      <td class="num">{fmt(cotisations)}</td>
      <td class="num">{fmt(cfp)}</td>
      <td class="num">{fmt(liberatoire)}</td>
      <td class="num charges">{fmt(total)}</td>
    </tr>"""

# ─── summary cards ────────────────────────────────────────────────────────────

summary = f"""<div class="cards">
  {card("HT encaissé", fmt(total_ht))}
  {card("Cotisations", fmt(total_cotisations))}
  {card("CFP", fmt(total_cfp))}
  {card("Libératoire", fmt(total_liberatoire))}
  {card("Total à payer", fmt(total_charges), "card-due")}
</div>"""

# ─── assemble ─────────────────────────────────────────────────────────────────

generated_at = datetime.now().strftime("%Y-%m-%d %H:%M")

html = f"""<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8"/>
<title>Trimestre view</title>
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
  .charges {{ color: #c62828; font-weight: 600; }}
  .empty-trim td {{ color: #ccc; }}
  .empty-trim .charges {{ color: #ddd; }}
  .total-row td {{ font-weight: 600; background: #f7f7f7; border-top: 2px solid #e0e0e0; }}
  .empty {{ color: #bbb; font-style: italic; }}
</style>
</head>
<body>

<h1>Charges sociales à payer — par trimestre</h1>
<div class="meta">Généré le {generated_at} · cotisations + CFP + versement libératoire, basé sur les encaissements (paiements reçus)</div>

{summary}

<h2>Par trimestre</h2>
<table>
  <thead>{th("Trimestre", "HT", "Cotisations", "CFP", "Libératoire", "Total à payer")}</thead>
  <tbody>{trim_rows or '<tr><td colspan="6" class="empty">Aucun encaissement</td></tr>'}</tbody>
</table>

<h2>Détail des encaissements</h2>
<table>
  <thead>{th("Date virement", "Trimestre", "Facture", "Client", "Projet", "HT", "Cotisations", "CFP", "Libératoire", "Total")}</thead>
  <tbody>{detail_rows or '<tr><td colspan="10" class="empty">Aucun encaissement</td></tr>'}</tbody>
</table>

</body>
</html>"""

# ─── write ────────────────────────────────────────────────────────────────────

out_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "exports", "view"))
os.makedirs(out_dir, exist_ok=True)
out_path = os.path.join(out_dir, "trimester.html")

with open(out_path, "w", encoding="utf-8") as f:
    f.write(html)

print(f"\n── trimestre ──")
for t in sorted(by_trim):
    d = by_trim[t]
    print(f"{t} >> HT : {d['ht']:g} | Cotisations : {d['cotisations']:g} | CFP : {d['cfp']:g} | Libératoire : {d['liberatoire']:g} | Total : {d['total']:g}")
print(f"\nTotal à payer : {total_charges:.2f} €")
print(f"view @ {out_path}")

if hasattr(os, "startfile"):
    os.startfile(os.path.normpath(out_path))

if configs.pause_on_exit: input("\nEntrée pour fermer...")
