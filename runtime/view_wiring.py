"""
Generate exports/view/wiring.html

3 tables:
  1. Virements reçus
  2. Factures (statut payé/partiel/en attente basé sur les associations explicites du .wire)
  3. Virements hors clients connus

Table 1 is editable: each row's "Facture" cell doubles as a form to
associate/reassign/clear that wire's bill (saved via app_gui.py's
associate_wire(), targeting the exact source file + line number recorded on
the Wire object -- see packages/database/wiring.py). A form at the top lets
you record a new received wire (add_wire()).
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
from packages.database.wiring import Wiring
from modules.layout import render_shell

# ─── load ─────────────────────────────────────────────────────────────────────

db = Database.init_billing()
wiring = Wiring()

wired_years = {w.date.year for w in wiring.wires}
known_uids  = {c.uid for c in db.clients}

known_wires   = [w for w in sorted(wiring.wires, key=lambda x: x.date) if w.client_uid in known_uids]
unknown_wires = [w for w in sorted(wiring.wires, key=lambda x: x.date) if w.client_uid not in known_uids]

# bills from wired years
bills = []
for p in db.projects:
    for b in p.bills:
        if b.getDatetime().year in wired_years:
            bills.append((p, b))
bills.sort(key=lambda x: x[1].uid)

# ─── build payment map from explicit bill_fuid associations ───────────────────
# paid_by_fuid[fuid] = list of wires that reference it
paid_by_fuid = defaultdict(list)
for w in known_wires:
    if w.bill_fuid:
        paid_by_fuid[w.bill_fuid].append(w)

# ─── helpers ──────────────────────────────────────────────────────────────────

def fmt(v):
    return f"{v:,.2f}".replace(",", " ") + " €"

def th(*cols):
    return "<tr>" + "".join(f"<th>{c}</th>" for c in cols) + "</tr>"

def card(label, value, cls=""):
    return f'<div class="card {cls}"><div class="card-label">{label}</div><div class="card-value">{value}</div></div>'

# ─── table 1 : virements reçus ────────────────────────────────────────────────

all_bill_fuids = sorted({(b.getFullUid() or b.uid) for p in db.projects for b in p.bills})
bill_fuids_datalist = "".join(f'<option value="{fuid}">' for fuid in all_bill_fuids)

wire_rows = ""
total_wires = 0.0
for w in known_wires:
    client = db.getClient(w.client_uid)
    name = client.name if client else w.client_uid
    filename = os.path.basename(w.source_file) if w.source_file else ""
    wire_rows += f"""<tr data-filename="{filename}" data-line="{w.line_no}">
      <td>{w.date:%Y-%m-%d}</td>
      <td>{name}</td>
      <td class="num">{fmt(w.amount)}</td>
      <td class="actions">
        <input type="text" class="fuid-input" list="bill-fuids" placeholder="aucune" value="{w.bill_fuid or ''}">
        <button class="save-btn" onclick="return associateWire(this)">Associer</button>
        <span class="row-status"></span>
      </td>
    </tr>"""
    total_wires += w.amount

wire_rows += f"""<tr class="total-row">
  <td colspan="2">Total</td>
  <td class="num">{fmt(total_wires)}</td>
  <td></td>
</tr>"""

# ─── table 2 : factures ───────────────────────────────────────────────────────

bill_rows = ""
total_billed = 0.0

for p, b in bills:
    client = b.getClient()
    if not client:
        continue

    fuid  = b.getFullUid() or b.uid
    ttc   = b.getTTC()
    wires = paid_by_fuid.get(fuid, [])
    received = sum(w.amount for w in wires)
    remaining = ttc - received
    last_wire_date = max((w.date for w in wires), default=None)

    if remaining <= 0.01:
        row_cls = "paid"
        status  = f"✓ {last_wire_date:%Y-%m-%d}" if last_wire_date else "✓"
        rem_cell = "—"
    elif received > 0.01:
        row_cls = "partial"
        status  = f"partiel"
        rem_cell = f'<span class="due">{fmt(remaining)}</span>'
    else:
        row_cls = "unpaid"
        status  = "en attente"
        rem_cell = f'<span class="due">{fmt(remaining)}</span>'

    total_billed += ttc
    bill_rows += f"""<tr class="{row_cls}">
      <td class="mono">{fuid}</td>
      <td>{b.uid}</td>
      <td>{client.name}</td>
      <td>{p.name}</td>
      <td class="num">{fmt(b.getHT())}</td>
      <td class="num">{fmt(ttc)}</td>
      <td class="num">{fmt(received) if received > 0 else "—"}</td>
      <td class="num">{rem_cell}</td>
      <td>{status}</td>
    </tr>"""

bill_rows += f"""<tr class="total-row">
  <td colspan="4">Total</td>
  <td></td>
  <td class="num">{fmt(total_billed)}</td>
  <td colspan="3"></td>
</tr>"""

# ─── table 3 : virements hors clients ─────────────────────────────────────────

unknown_rows = ""
total_unknown = 0.0
for w in unknown_wires:
    unknown_rows += f"""<tr>
      <td>{w.date:%Y-%m-%d}</td>
      <td class="mono">{w.client_uid}</td>
      <td class="num">{fmt(w.amount)}</td>
    </tr>"""
    total_unknown += w.amount
if unknown_rows:
    unknown_rows += f'<tr class="total-row"><td colspan="2">Total</td><td class="num">{fmt(total_unknown)}</td></tr>'

# ─── summary cards ────────────────────────────────────────────────────────────

# compute from per-bill data, not from global wire totals
total_received_on_bills = 0.0
total_remaining = 0.0
for p, b in bills:
    client = b.getClient()
    if not client:
        continue
    fuid = b.getFullUid() or b.uid
    wires_for_bill = paid_by_fuid.get(fuid, [])
    received = sum(w.amount for w in wires_for_bill)
    total_received_on_bills += received
    total_remaining += max(0.0, b.getTTC() - received)

summary = f"""<div class="cards">
  {card("Facturé TTC", fmt(total_billed))}
  {card("Reçu (sur ces factures)", fmt(total_received_on_bills))}
  {card("Restant", fmt(total_remaining), "card-due" if total_remaining > 0.01 else "card-ok")}
</div>"""

# ─── add-wire form ─────────────────────────────────────────────────────────────

client_options = "".join(
    f'<option value="{c.uid}">{c.name}</option>' for c in sorted(db.clients, key=lambda c: c.name)
)

add_wire_form = f"""
<div class="add-wire-form">
  <h3>Ajouter un virement</h3>
  <label>Client
    <select class="new-wire-client">{client_options}</select>
  </label>
  <label>Date<input type="text" class="new-wire-date" placeholder="AAAA-MM-JJ"></label>
  <label>Montant TTC<input type="text" class="new-wire-amount" placeholder="0"></label>
  <label>Facture (optionnel)<input type="text" class="new-wire-fuid" list="bill-fuids" placeholder="aucune"></label>
  <button onclick="return addWire(this)">Ajouter</button>
  <span class="add-status"></span>
</div>"""

# ─── assemble ─────────────────────────────────────────────────────────────────

unknown_section = f"""
<h2>Virements hors clients connus</h2>
<table data-default-sort="0:asc">
  <thead>{th("Date", "UID reçu", "Montant")}</thead>
  <tbody>{unknown_rows}</tbody>
</table>""" if unknown_wires else ""

generated_at = datetime.now().strftime("%Y-%m-%d %H:%M")

page_style = """
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { font-family: system-ui, sans-serif; font-size: 14px; background: #f5f5f5; color: #222; }
  h1 { font-size: 20px; font-weight: 700; margin-bottom: 4px; }
  .meta { color: #888; font-size: 12px; margin-bottom: 24px; }
  h2 { font-size: 11px; font-weight: 600; text-transform: uppercase; letter-spacing: .06em;
        color: #999; margin: 32px 0 10px; }

  .cards { display: flex; gap: 12px; flex-wrap: wrap; margin-bottom: 28px; }
  .card { background: #fff; border-radius: 8px; padding: 14px 20px; min-width: 140px;
            box-shadow: 0 1px 3px rgba(0,0,0,.07); }
  .card-label { font-size: 10px; color: #aaa; text-transform: uppercase; letter-spacing: .05em; }
  .card-value { font-size: 20px; font-weight: 700; margin-top: 4px; }
  .card-due .card-value { color: #c62828; }
  .card-ok  .card-value { color: #2e7d32; }

  table { width: 100%; border-collapse: collapse; background: #fff; border-radius: 8px;
            overflow: hidden; box-shadow: 0 1px 3px rgba(0,0,0,.07); margin-bottom: 4px; }
  th { background: #f0f0f0; text-align: left; padding: 7px 12px;
        font-size: 10px; text-transform: uppercase; letter-spacing: .05em; color: #888; }
  td { padding: 7px 12px; border-top: 1px solid #f0f0f0; vertical-align: middle; }
  tr:hover td { background: #fafafa; }
  .num { text-align: left; font-variant-numeric: tabular-nums; white-space: nowrap; }
  .mono { font-family: monospace; font-size: 12px; color: #777; }
  .empty { color: #ccc; }
  .ref { font-family: monospace; font-size: 11px; color: #888; }
  .due { color: #c62828; font-weight: 600; }
  .total-row td { font-weight: 600; background: #f7f7f7; border-top: 2px solid #e0e0e0; }

  tr.paid td   { color: #bbb; }
  tr.paid .mono { color: #ccc; }
  tr.partial td { background: #fff8e1; }

  /* add-wire form */
  .add-wire-form { background: #fff; border-radius: 8px; padding: 16px 20px;
                     box-shadow: 0 1px 3px rgba(0,0,0,.07); display: flex;
                     align-items: flex-end; gap: 16px; flex-wrap: wrap; margin-bottom: 28px; }
  .add-wire-form h3 { flex-basis: 100%; font-size: 13px; font-weight: 700; color: #555; margin-bottom: 4px; }
  .add-wire-form label { display: flex; flex-direction: column; gap: 4px; font-size: 11px;
                           color: #888; text-transform: uppercase; letter-spacing: .04em; }
  .add-wire-form input, .add-wire-form select { padding: 6px 8px; border: 1px solid #ddd; border-radius: 5px;
                           font-size: 13px; font-family: inherit; width: 140px; }
  .add-wire-form input:focus, .add-wire-form select:focus { outline: none; border-color: #888; }
  .add-wire-form button { padding: 7px 16px; border: none; border-radius: 20px;
                            background: #2e7d32; color: #fff; cursor: pointer;
                            font-size: 12px; font-weight: 600; }
  .add-wire-form button:hover { background: #256428; }
  .add-wire-form button:disabled { opacity: .5; cursor: default; }
  .add-status { font-size: 12px; }
  .add-status.ok { color: #2e7d32; font-weight: 600; }
  .add-status.err { color: #c62828; font-weight: 600; }

  /* per-row associate control */
  .actions { display: flex; align-items: center; gap: 8px; white-space: nowrap; }
  .fuid-input { width: 130px; padding: 5px 8px; border: 1px solid #ddd; border-radius: 5px;
                 font-size: 12px; font-family: monospace; }
  .fuid-input:focus { outline: none; border-color: #888; }
  .save-btn { padding: 6px 14px; border: none; border-radius: 14px;
               background: #222; color: #fff; cursor: pointer; font-size: 12px; font-weight: 600; }
  .save-btn:hover { background: #444; }
  .save-btn:disabled { opacity: .5; cursor: default; }
  .row-status { font-size: 12px; }
  .row-status.ok { color: #2e7d32; font-weight: 600; }
  .row-status.err { color: #c62828; font-weight: 600; }
"""

RELOAD_SCRIPT = """
async function reloadAfterEdit() {
  if (!(window.pywebview && window.pywebview.api)) return;
  document.body.style.cursor = 'wait';
  try { await window.pywebview.api.run('wiring.html'); } catch (e) {}
  window.location.reload();
}

async function associateWire(btn) {
  const row = btn.closest('tr');
  const status = row.querySelector('.row-status');
  if (!(window.pywebview && window.pywebview.api)) {
    status.textContent = "Indisponible en dehors de l'application.";
    return false;
  }
  const filename = row.dataset.filename;
  const line = row.dataset.line;
  const fuid = row.querySelector('.fuid-input').value.trim();
  btn.disabled = true;
  status.textContent = '';
  status.className = 'row-status';
  const result = await window.pywebview.api.associate_wire(filename, line, fuid);
  btn.disabled = false;
  if (result && result.ok) {
    status.textContent = 'Enregistré ✓';
    status.className = 'row-status ok';
    await reloadAfterEdit();
  } else {
    status.textContent = 'Erreur : ' + (result && result.error || '?');
    status.className = 'row-status err';
  }
  return false;
}

async function addWire(btn) {
  const wrap = btn.closest('.add-wire-form');
  const status = wrap.querySelector('.add-status');
  if (!(window.pywebview && window.pywebview.api)) {
    status.textContent = "Indisponible en dehors de l'application.";
    return false;
  }
  const client = wrap.querySelector('.new-wire-client').value;
  const date   = wrap.querySelector('.new-wire-date').value.trim();
  const amount = wrap.querySelector('.new-wire-amount').value.trim();
  const fuid   = wrap.querySelector('.new-wire-fuid').value.trim();
  if (!client || !date || !amount) {
    status.textContent = 'Client, date et montant sont requis.';
    status.className = 'add-status err';
    return false;
  }
  btn.disabled = true;
  status.textContent = '';
  status.className = 'add-status';
  const result = await window.pywebview.api.add_wire(client, date, amount, fuid);
  btn.disabled = false;
  if (result && result.ok) {
    status.textContent = 'Virement ajouté ✓';
    status.className = 'add-status ok';
    await reloadAfterEdit();
  } else {
    status.textContent = 'Erreur : ' + (result && result.error || '?');
    status.className = 'add-status err';
  }
  return false;
}
"""

body_content = f"""
<h1>Virements</h1>
<div class="meta">Généré le {generated_at} — les dates acceptent AAAA-MM-JJ</div>

<datalist id="bill-fuids">{bill_fuids_datalist}</datalist>

{summary}

{add_wire_form}

<h2>Virements reçus</h2>
<table data-default-sort="0:asc">
  <thead>{th("Date", "Client", "Montant TTC", "Facture")}</thead>
  <tbody>{wire_rows}</tbody>
</table>

<script>{RELOAD_SCRIPT}</script>

<h2>Factures</h2>
<table data-default-sort="1:asc">
  <thead>{th("#", "Date émise", "Client", "Projet", "HT", "TTC", "Reçu", "Restant", "Statut")}</thead>
  <tbody>{bill_rows}</tbody>
</table>

{unknown_section}
"""

html = render_shell("Wiring view", "wiring.html", body_content, page_style)

# ─── write ────────────────────────────────────────────────────────────────────

out_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "exports", "view"))
os.makedirs(out_dir, exist_ok=True)
out_path = os.path.join(out_dir, "wiring.html")

with open(out_path, "w", encoding="utf-8") as f:
    f.write(html)

print(f"\n── wiring ──")
print(f"virements    : {len(wiring.wires)}")
print(f"facturés TTC : {total_billed:.2f} €")
print(f"reçu         : {total_received_on_bills:.2f} €")
print(f"restant      : {total_remaining:.2f} €")
if unknown_wires:
    print(f"hors clients : {len(unknown_wires)} virement(s)")
print(f"view @ {out_path}")

if hasattr(os, "startfile") and not configs.webview_mode:
    os.startfile(os.path.normpath(out_path))

if configs.pause_on_exit and not configs.webview_mode: input("\nEntrée pour fermer...")
