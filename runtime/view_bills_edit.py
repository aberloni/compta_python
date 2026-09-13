"""
Generate exports/view/bills_edit.html — édition des factures.

One tab per project. Each tab lists that project's bills with editable
start/end period fields (saved via app_gui.py's update_bill_range()), plus a
form to add a new bill for that project (add_bill()). Only the period is
editable here — forfait/frais/label overrides stay file-only, edited by hand.
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
from packages.database.wiring import Wiring
from modules.layout import render_shell

# ─── load ─────────────────────────────────────────────────────────────────────

db = Database.init_billing()
wiring = Wiring()

# full UIDs of bills that already have at least one wire linked to them --
# those can't be deleted (see tools/bill_editor.py: delete_bill())
linked_fuids = {w.bill_fuid for w in wiring.wires if w.bill_fuid}

# ─── helpers ──────────────────────────────────────────────────────────────────

def fmt_eur(v):
    return f"{v:,.2f}&nbsp;€".replace(",", " ")

def fmt_days(v):
    return f"{v:g}"

def th(*cols):
    return "<tr>" + "".join(f"<th>{c}</th>" for c in cols) + "</tr>"

# ─── per-project tab ────────────────────────────────────────────────────────

def build_project_tab(p):
    bills = sorted(p.bills, key=lambda b: b.uid, reverse=True)

    rows = ""
    for b in bills:
        fuid = b.getFullUid() or b.uid
        tags = ""
        if b.isForfait():
            tags += '<span class="tag forfait">forfait</span>'
        if b.hasTransactions():
            tags += '<span class="tag">+frais</span>'
        if b.label:
            tags += '<span class="tag label">label</span>'

        client = b.getClient()
        client_name = client.name if client else "?"

        if fuid in linked_fuids:
            delete_btn = ('<button class="delete-btn" disabled '
                          'title="Virement(s) déjà associé(s) : suppression impossible">Supprimer</button>')
        else:
            delete_btn = '<button class="delete-btn" onclick="return deleteBill(this)">Supprimer</button>'

        rows += f"""<tr data-project="{p.uid}" data-bill="{b.uid}">
          <td class="mono">{fuid}</td>
          <td>{b.uid}{tags}</td>
          <td>{client_name}</td>
          <td><input type="text" class="range-input start-input" value="{b.start:%Y-%m-%d}"></td>
          <td><input type="text" class="range-input end-input" value="{b.end:%Y-%m-%d}"></td>
          <td class="num">{fmt_days(b.countDays())}&nbsp;j</td>
          <td class="num">{fmt_eur(b.getHT())}</td>
          <td class="num">{fmt_eur(b.getTTC())}</td>
          <td class="actions">
            <button class="save-btn" onclick="return saveBillRange(this)">Enregistrer</button>
            <button class="pdf-btn" onclick="return generateBillPdf(this)">PDF</button>
            {delete_btn}
            <span class="row-status"></span>
          </td>
        </tr>"""

    table_html = f"""
    <table data-default-sort="1:desc">
      <thead>{th("ID", "Date facture", "Client", "Début", "Fin", "Jours", "HT", "TTC", "")}</thead>
      <tbody>{rows or '<tr><td colspan="9" class="empty">Aucune facture</td></tr>'}</tbody>
    </table>"""

    return table_html

# ─── build tabs ───────────────────────────────────────────────────────────────

projects = sorted(db.projects, key=lambda p: p.name)

tabs_nav = ""
tabs_content = ""
for i, p in enumerate(projects):
    tid = f"tab-{p.uid}"
    active = "active" if i == 0 else ""
    tabs_nav     += f'<button class="tab-btn {active}" onclick="showTab(\'{tid}\')" id="btn-{tid}">{p.name}</button>'
    tabs_content += f'<div class="tab-panel {active}" id="{tid}" data-project="{p.uid}">{build_project_tab(p)}</div>'

first_project_uid = projects[0].uid if projects else ""
project_names_js = "{" + ",".join(f'"{p.uid}":"{p.name}"' for p in projects) + "}"

# ─── assemble ─────────────────────────────────────────────────────────────────

generated_at = datetime.now().strftime("%Y-%m-%d %H:%M")

RELOAD_SCRIPT = """
async function reloadAfterEdit() {
  if (!(window.pywebview && window.pywebview.api)) return;
  document.body.style.cursor = 'wait';
  try { await window.pywebview.api.run('bills_edit.html'); } catch (e) {}
  window.location.reload();
}

async function saveBillRange(btn) {
  const row = btn.closest('tr');
  const status = row.querySelector('.row-status');
  if (!(window.pywebview && window.pywebview.api)) {
    status.textContent = "Indisponible en dehors de l'application.";
    return false;
  }
  const projectUid = row.dataset.project;
  const billUid = row.dataset.bill;
  const start = row.querySelector('.start-input').value.trim();
  const end = row.querySelector('.end-input').value.trim();
  if (!start || !end) {
    status.textContent = 'Début et fin sont requis.';
    status.className = 'row-status err';
    return false;
  }
  btn.disabled = true;
  status.textContent = '';
  status.className = 'row-status';
  const result = await window.pywebview.api.update_bill_range(projectUid, billUid, start, end);
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

async function generateBillPdf(btn) {
  const row = btn.closest('tr');
  const status = row.querySelector('.row-status');
  if (!(window.pywebview && window.pywebview.api)) {
    status.textContent = "Indisponible en dehors de l'application.";
    return false;
  }
  const projectUid = row.dataset.project;
  const billUid = row.dataset.bill;
  btn.disabled = true;
  status.textContent = 'Génération…';
  status.className = 'row-status';
  const result = await window.pywebview.api.generate_bill_pdf(projectUid, billUid);
  btn.disabled = false;
  if (result && result.ok) {
    status.textContent = 'PDF généré ✓';
    status.className = 'row-status ok';
  } else {
    status.textContent = 'Erreur : ' + (result && result.error || '?');
    status.className = 'row-status err';
  }
  return false;
}

async function deleteBill(btn) {
  const row = btn.closest('tr');
  const status = row.querySelector('.row-status');
  if (!(window.pywebview && window.pywebview.api)) {
    status.textContent = "Indisponible en dehors de l'application.";
    return false;
  }
  const projectUid = row.dataset.project;
  const billUid = row.dataset.bill;
  if (!confirm('Supprimer la facture ' + billUid + ' ?\\n\\nCette action est irréversible.')) {
    return false;
  }
  btn.disabled = true;
  status.textContent = '';
  status.className = 'row-status';
  const result = await window.pywebview.api.delete_bill(projectUid, billUid);
  btn.disabled = false;
  if (result && result.ok) {
    status.textContent = 'Supprimée ✓';
    status.className = 'row-status ok';
    await reloadAfterEdit();
  } else {
    status.textContent = 'Erreur : ' + (result && result.error || '?');
    status.className = 'row-status err';
  }
  return false;
}

function openAddBillModal() {
  const overlay = document.getElementById('add-bill-overlay');
  const status = document.getElementById('add-bill-status');
  document.getElementById('add-bill-project-name').textContent = PROJECT_NAMES[currentProjectUid] || currentProjectUid;
  document.getElementById('add-bill-date').value = '';
  document.getElementById('add-bill-start').value = '';
  document.getElementById('add-bill-end').value = '';
  status.textContent = '';
  status.className = 'add-status';
  overlay.hidden = false;
  document.getElementById('add-bill-date').focus();
  return false;
}

function closeAddBillModal() {
  document.getElementById('add-bill-overlay').hidden = true;
  return false;
}

function onOverlayClick(event) {
  if (event.target.id === 'add-bill-overlay') closeAddBillModal();
  return false;
}

document.addEventListener('keydown', function (event) {
  if (event.key === 'Escape' && !document.getElementById('add-bill-overlay').hidden) {
    closeAddBillModal();
  }
});

async function submitAddBill(btn) {
  const status = document.getElementById('add-bill-status');
  if (!(window.pywebview && window.pywebview.api)) {
    status.textContent = "Indisponible en dehors de l'application.";
    status.className = 'add-status err';
    return false;
  }
  const projectUid = currentProjectUid;
  const date  = document.getElementById('add-bill-date').value.trim();
  const start = document.getElementById('add-bill-start').value.trim();
  const end   = document.getElementById('add-bill-end').value.trim();
  if (!projectUid || !date || !start || !end) {
    status.textContent = 'Tous les champs sont requis.';
    status.className = 'add-status err';
    return false;
  }
  btn.disabled = true;
  status.textContent = '';
  status.className = 'add-status';
  const result = await window.pywebview.api.add_bill(projectUid, date, start, end);
  btn.disabled = false;
  if (result && result.ok) {
    status.textContent = 'Facture ajoutée ✓';
    status.className = 'add-status ok';
    await reloadAfterEdit();
  } else {
    status.textContent = 'Erreur : ' + (result && result.error || '?');
    status.className = 'add-status err';
  }
  return false;
}
"""

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

  /* table */
  table { width: 100%; border-collapse: collapse; background: #fff;
            border-radius: 8px; overflow: hidden;
            box-shadow: 0 1px 3px rgba(0,0,0,.07); margin-bottom: 24px; }
  th { background: #f0f0f0; text-align: left; padding: 7px 12px;
        font-size: 10px; text-transform: uppercase; letter-spacing: .05em; color: #888; }
  td { padding: 7px 12px; border-top: 1px solid #f0f0f0; vertical-align: middle; }
  tr:hover td { background: #fafafa; }
  .num { text-align: left; font-variant-numeric: tabular-nums; white-space: nowrap; }
  .mono { font-family: monospace; font-size: 12px; color: #777; }
  .empty { color: #bbb; font-style: italic; }
  .tag { font-size: 10px; background: #e8f0fe; color: #3367d6;
          border-radius: 4px; padding: 2px 6px; margin-left: 6px; white-space: nowrap; }
  .tag.forfait { background: #fce8b2; color: #b06000; }
  .tag.label { background: #e6f4ea; color: #2e7d32; }

  .range-input { width: 100px; padding: 5px 8px; border: 1px solid #ddd; border-radius: 5px;
                  font-size: 13px; font-family: inherit; }
  .range-input:focus { outline: none; border-color: #888; }

  .actions { display: flex; align-items: center; gap: 8px; white-space: nowrap; }
  .save-btn { padding: 6px 14px; border: none; border-radius: 14px;
               background: #222; color: #fff; cursor: pointer; font-size: 12px; font-weight: 600; }
  .save-btn:hover { background: #444; }
  .save-btn:disabled { opacity: .5; cursor: default; }
  .pdf-btn { padding: 6px 14px; border: none; border-radius: 14px;
              background: #3367d6; color: #fff; cursor: pointer; font-size: 12px; font-weight: 600; }
  .pdf-btn:hover { background: #2851ad; }
  .pdf-btn:disabled { opacity: .5; cursor: default; }
  .delete-btn { padding: 6px 14px; border: none; border-radius: 14px;
                 background: #c62828; color: #fff; cursor: pointer; font-size: 12px; font-weight: 600; }
  .delete-btn:hover { background: #a01f1f; }
  .delete-btn:disabled { opacity: .35; cursor: not-allowed; background: #999; }
  .row-status, .add-status { font-size: 12px; }
  .row-status.ok, .add-status.ok { color: #2e7d32; font-weight: 600; }
  .row-status.err, .add-status.err { color: #c62828; font-weight: 600; }

  /* floating "add bill" button */
  .fab { position: fixed; bottom: 32px; right: 32px; width: 56px; height: 56px;
          border-radius: 50%; border: none; background: #2e7d32; color: #fff;
          font-size: 28px; line-height: 1; cursor: pointer;
          box-shadow: 0 3px 10px rgba(0,0,0,.25); display: flex;
          align-items: center; justify-content: center; z-index: 900; }
  .fab:hover { background: #256428; }

  /* add-bill overlay + modal */
  .overlay { position: fixed; inset: 0; background: rgba(0,0,0,.4);
              display: flex; align-items: center; justify-content: center; z-index: 1500; }
  .overlay[hidden] { display: none; }
  .modal { background: #fff; border-radius: 10px; padding: 24px 28px;
            width: 320px; box-shadow: 0 10px 30px rgba(0,0,0,.2);
            display: flex; flex-direction: column; gap: 14px; }
  .modal h3 { font-size: 15px; font-weight: 700; color: #333; }
  .modal label { display: flex; flex-direction: column; gap: 5px; font-size: 11px;
                  color: #888; text-transform: uppercase; letter-spacing: .04em; }
  .modal input { padding: 7px 9px; border: 1px solid #ddd; border-radius: 5px;
                  font-size: 13px; font-family: inherit; }
  .modal input:focus { outline: none; border-color: #888; }
  .modal-project-name { padding: 7px 0; font-size: 14px; font-weight: 600; color: #333; }
  .modal-actions { display: flex; justify-content: flex-end; gap: 10px; }
  .modal-actions button { padding: 7px 16px; border: none; border-radius: 20px;
                            cursor: pointer; font-size: 12px; font-weight: 600; }
  .modal-cancel { background: #eee; color: #555; }
  .modal-cancel:hover { background: #ddd; }
  .modal-submit { background: #2e7d32; color: #fff; }
  .modal-submit:hover { background: #256428; }
  .modal-submit:disabled { opacity: .5; cursor: default; }
"""

body_content = f"""
<h1>Éditer les factures</h1>
<div class="meta">Généré le {generated_at} — les dates acceptent AAAA-MM-JJ, AAAA-MM ou AAAA</div>

<div class="tabs-nav">{tabs_nav}</div>

{tabs_content}

<button id="add-bill-fab" class="fab" onclick="return openAddBillModal()" title="Ajouter une facture">+</button>

<div id="add-bill-overlay" class="overlay" onclick="return onOverlayClick(event)" hidden>
  <div class="modal">
    <h3>Ajouter une facture</h3>
    <label>Projet
      <div id="add-bill-project-name" class="modal-project-name"></div>
    </label>
    <label>Date facture
      <input type="text" id="add-bill-date" placeholder="AAAA-MM-JJ">
    </label>
    <label>Début
      <input type="text" id="add-bill-start" placeholder="AAAA-MM-JJ">
    </label>
    <label>Fin
      <input type="text" id="add-bill-end" placeholder="AAAA-MM-JJ">
    </label>
    <div class="modal-actions">
      <span id="add-bill-status" class="add-status"></span>
      <button class="modal-cancel" onclick="return closeAddBillModal()">Annuler</button>
      <button class="modal-submit" onclick="return submitAddBill(this)">Ajouter</button>
    </div>
  </div>
</div>

<script>{RELOAD_SCRIPT}</script>

<script>
const PROJECT_NAMES = {project_names_js};
let currentProjectUid = "{first_project_uid}";

function showTab(id) {{
  document.querySelectorAll('.tab-panel').forEach(el => el.classList.remove('active'));
  document.querySelectorAll('.tab-btn').forEach(el => el.classList.remove('active'));
  const panel = document.getElementById(id);
  panel.classList.add('active');
  document.getElementById('btn-' + id).classList.add('active');
  currentProjectUid = panel.dataset.project;
}}
</script>
"""

html = render_shell("Éditer les factures", "bills_edit.html", body_content, page_style)

# ─── write ────────────────────────────────────────────────────────────────────

out_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "exports", "view"))
os.makedirs(out_dir, exist_ok=True)
out_path = os.path.join(out_dir, "bills_edit.html")

with open(out_path, "w", encoding="utf-8") as f:
    f.write(html)

print(f"\n── bills_edit ──")
print(f"projets  : {len(projects)}")
print(f"factures : {sum(len(p.bills) for p in projects)}")
print(f"\nview @ {out_path}")

if hasattr(os, "startfile") and not configs.webview_mode:
    os.startfile(os.path.normpath(out_path))

if configs.pause_on_exit and not configs.webview_mode: input("\nEntrée pour fermer...")
