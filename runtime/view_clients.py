"""
Generate exports/view/clients.html — édition des clients.

One tab per client (same "pick one, see only that one" pattern as the other
pages' project tabs). Each tab shows that client's editable fields (name,
address, creditor, country, tva number, color), saved via app_gui.py's
update_client(). A "+" button opens a modal to add a new client
(add_client()). uid is never editable here -- it's the filename itself, and
projects/ + wiring/ files reference it (see tools/client_editor.py).
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

# ISO 3166-1 alpha-2 codes -- matches infos/{ISO}.info filenames (see
# Client.getCountryInfo()). Not an exhaustive list, just the countries a
# French freelancer is realistically likely to bill -- the field stays free
# text (this only powers the <datalist> suggestions).
COUNTRIES = [
    ("FR", "France"), ("BE", "Belgique"), ("CH", "Suisse"), ("LU", "Luxembourg"),
    ("DE", "Allemagne"), ("ES", "Espagne"), ("IT", "Italie"), ("PT", "Portugal"),
    ("NL", "Pays-Bas"), ("GB", "Royaume-Uni"), ("IE", "Irlande"), ("AT", "Autriche"),
    ("PL", "Pologne"), ("SE", "Suède"), ("DK", "Danemark"), ("FI", "Finlande"),
    ("NO", "Norvège"), ("GR", "Grèce"), ("CZ", "Tchéquie"), ("RO", "Roumanie"),
    ("US", "États-Unis"), ("CA", "Canada"), ("MA", "Maroc"), ("TN", "Tunisie"),
    ("DZ", "Algérie"), ("SN", "Sénégal"), ("AU", "Australie"), ("JP", "Japon"),
    ("CN", "Chine"), ("IN", "Inde"), ("BR", "Brésil"), ("MX", "Mexique"),
]

# ─── helpers ──────────────────────────────────────────────────────────────────

def esc(v):
    return (v or "").replace('"', "&quot;")

def project_names_for(client_uid):
    return [p.name for p in db.projects if p.client and p.client.uid == client_uid]

def field(label, input_html):
    return f'<div class="field"><label>{label}</label>{input_html}</div>'

country_datalist = "<datalist id=\"country-list\">" + "".join(
    f'<option value="{code}">{name}</option>' for code, name in COUNTRIES
) + "</datalist>"

# ─── per-client tab ───────────────────────────────────────────────────────────

def split_address(address):
    """(street, city) from the stored 'street|city' address, city empty if no '|'."""
    street, sep, city = (address or "").partition("|")
    return street, city

def build_client_panel(c):
    projects = project_names_for(c.uid)
    projects_cell = ", ".join(projects) if projects else '<span class="empty">aucun</span>'
    picker_value = c.color if c.color else "#cccccc"
    street, city = split_address(c.address)

    return f"""<div class="client-form" data-uid="{c.uid}">
      {field("UID", f'<div class="mono">{c.uid}</div>')}
      {field("Nom", f'<input type="text" class="edit-input name-input" value="{esc(c.name)}">')}
      {field("Adresse", f'<input type="text" class="edit-input address-street-input" value="{esc(street)}" placeholder="12-14 rue Jean-Jacques Rousseau">')}
      {field("Ville", f'<input type="text" class="edit-input address-city-input" value="{esc(city)}" placeholder="93100 MONTREUIL">')}
      {field("Creditor (libellé relevé bancaire)", f'<input type="text" class="edit-input creditor-input" value="{esc(c.creditor)}">')}
      {field("Pays", f'<input type="text" class="edit-input country-input narrow" list="country-list" value="{esc(c.country)}" placeholder="FR">')}
      {field("N° TVA", f'<input type="text" class="edit-input tva-input" value="{esc(c.tva_number)}">')}
      {field("Couleur", f'''<div class="color-cell">
        <input type="color" class="color-picker" value="{picker_value}" oninput="return syncColorFromPicker(this)">
        <input type="text" class="edit-input color-input narrow" value="{esc(c.color)}" placeholder="#rrggbb" oninput="return syncColorFromText(this)">
      </div>''')}
      {field("Projets", f'<div>{projects_cell}</div>')}
      <div class="actions">
        <button class="save-btn" onclick="return saveClient(this)">Enregistrer</button>
        <span class="row-status"></span>
      </div>
    </div>"""

# ─── build tabs ───────────────────────────────────────────────────────────────

clients = sorted(db.clients, key=lambda c: c.name or c.uid)

tabs_nav = ""
tabs_content = ""
for i, c in enumerate(clients):
    tid = f"tab-{c.uid}"
    active = "active" if i == 0 else ""
    tabs_nav     += f'<button class="tab-btn {active}" onclick="showTab(\'{tid}\')" id="btn-{tid}">{c.name}</button>'
    tabs_content += f'<div class="tab-panel {active}" id="{tid}">{build_client_panel(c)}</div>'

if not clients:
    tabs_content = '<div class="empty">Aucun client</div>'

# ─── assemble ─────────────────────────────────────────────────────────────────

generated_at = datetime.now().strftime("%Y-%m-%d %H:%M")

RELOAD_SCRIPT = """
function showTab(id) {
  document.querySelectorAll('.tab-panel').forEach(el => el.classList.remove('active'));
  document.querySelectorAll('.tab-btn').forEach(el => el.classList.remove('active'));
  document.getElementById(id).classList.add('active');
  document.getElementById('btn-' + id).classList.add('active');
}

const HEX_COLOR_RE = /^#([0-9a-f]{6}|[0-9a-f]{3})$/i;

function syncColorFromPicker(picker) {
  const text = picker.closest('.color-cell').querySelector('.color-input');
  text.value = picker.value;
  return false;
}

function syncColorFromText(text) {
  const picker = text.closest('.color-cell').querySelector('.color-picker');
  if (HEX_COLOR_RE.test(text.value.trim())) {
    picker.value = text.value.trim();
  }
  return false;
}

async function reloadAfterEdit() {
  if (!(window.pywebview && window.pywebview.api)) return;
  document.body.style.cursor = 'wait';
  try { await window.pywebview.api.run('clients.html'); } catch (e) {}
  window.location.reload();
}

async function saveClient(btn) {
  const form = btn.closest('.client-form');
  const status = form.querySelector('.row-status');
  if (!(window.pywebview && window.pywebview.api)) {
    status.textContent = "Indisponible en dehors de l'application.";
    return false;
  }
  const uid = form.dataset.uid;
  const name = form.querySelector('.name-input').value.trim();
  const street = form.querySelector('.address-street-input').value.trim();
  const city = form.querySelector('.address-city-input').value.trim();
  const address = city ? street + '|' + city : street;
  const creditor = form.querySelector('.creditor-input').value.trim();
  const country = form.querySelector('.country-input').value.trim();
  const tva = form.querySelector('.tva-input').value.trim();
  const color = form.querySelector('.color-input').value.trim();
  if (!name || !street) {
    status.textContent = 'Nom et adresse sont requis.';
    status.className = 'row-status err';
    return false;
  }
  btn.disabled = true;
  status.textContent = '';
  status.className = 'row-status';
  const result = await window.pywebview.api.update_client(uid, name, address, creditor, country, tva, color);
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

function openAddClientModal() {
  const overlay = document.getElementById('add-client-overlay');
  const status = document.getElementById('add-client-status');
  ['uid', 'name', 'address-street', 'address-city', 'creditor', 'country', 'tva', 'color'].forEach(function (id) {
    document.getElementById('add-client-' + id).value = '';
  });
  document.getElementById('add-client-color-picker').value = '#cccccc';
  status.textContent = '';
  status.className = 'add-status';
  overlay.hidden = false;
  document.getElementById('add-client-uid').focus();
  return false;
}

function closeAddClientModal() {
  document.getElementById('add-client-overlay').hidden = true;
  return false;
}

function onOverlayClick(event) {
  if (event.target.id === 'add-client-overlay') closeAddClientModal();
  return false;
}

document.addEventListener('keydown', function (event) {
  if (event.key === 'Escape' && !document.getElementById('add-client-overlay').hidden) {
    closeAddClientModal();
  }
});

async function submitAddClient(btn) {
  const status = document.getElementById('add-client-status');
  if (!(window.pywebview && window.pywebview.api)) {
    status.textContent = "Indisponible en dehors de l'application.";
    status.className = 'add-status err';
    return false;
  }
  const uid = document.getElementById('add-client-uid').value.trim();
  const name = document.getElementById('add-client-name').value.trim();
  const street = document.getElementById('add-client-address-street').value.trim();
  const city = document.getElementById('add-client-address-city').value.trim();
  const address = city ? street + '|' + city : street;
  const creditor = document.getElementById('add-client-creditor').value.trim();
  const country = document.getElementById('add-client-country').value.trim();
  const tva = document.getElementById('add-client-tva').value.trim();
  const color = document.getElementById('add-client-color').value.trim();
  if (!uid || !name || !street) {
    status.textContent = 'UID, nom et adresse sont requis.';
    status.className = 'add-status err';
    return false;
  }
  btn.disabled = true;
  status.textContent = '';
  status.className = 'add-status';
  const result = await window.pywebview.api.add_client(uid, name, address, creditor, country, tva, color);
  btn.disabled = false;
  if (result && result.ok) {
    status.textContent = 'Client ajouté ✓';
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

  .mono { font-family: monospace; font-size: 13px; color: #555; }
  .empty { color: #bbb; font-style: italic; }

  /* tabs */
  .tabs-nav { display: flex; flex-wrap: wrap; gap: 6px; margin-bottom: 24px; }
  .tab-btn { padding: 7px 16px; border: 1px solid #ddd; border-radius: 20px;
              background: #fff; cursor: pointer; font-size: 13px; font-weight: 500;
              color: #555; transition: background .15s, color .15s; }
  .tab-btn:hover { background: #f0f0f0; }
  .tab-btn.active { background: #222; color: #fff; border-color: #222; }
  .tab-panel { display: none; }
  .tab-panel.active { display: block; }

  /* per-client form */
  .client-form { background: #fff; border-radius: 8px; padding: 24px 28px;
                  max-width: 420px; box-shadow: 0 1px 3px rgba(0,0,0,.07); }
  .field { display: flex; flex-direction: column; gap: 5px; margin-bottom: 16px; }
  .field label { font-size: 11px; color: #888; text-transform: uppercase; letter-spacing: .04em; }
  .edit-input { width: 100%; padding: 7px 9px; border: 1px solid #ddd; border-radius: 5px;
                 font-size: 13px; font-family: inherit; }
  .edit-input:focus { outline: none; border-color: #888; }
  .edit-input.narrow { width: 100px; }
  .color-cell { display: flex; align-items: center; gap: 6px; }
  .color-picker { width: 32px; height: 32px; padding: 2px; border: 1px solid #ddd; border-radius: 5px;
                    cursor: pointer; flex-shrink: 0; background: #fff; }

  .actions { display: flex; align-items: center; gap: 10px; margin-top: 4px; }
  .save-btn { padding: 6px 14px; border: none; border-radius: 14px;
               background: #222; color: #fff; cursor: pointer; font-size: 12px; font-weight: 600; }
  .save-btn:hover { background: #444; }
  .save-btn:disabled { opacity: .5; cursor: default; }
  .row-status, .add-status { font-size: 12px; }
  .row-status.ok, .add-status.ok { color: #2e7d32; font-weight: 600; }
  .row-status.err, .add-status.err { color: #c62828; font-weight: 600; }

  /* floating "add client" button */
  .fab { position: fixed; bottom: 32px; right: 32px; width: 56px; height: 56px;
          border-radius: 50%; border: none; background: #2e7d32; color: #fff;
          font-size: 28px; line-height: 1; cursor: pointer;
          box-shadow: 0 3px 10px rgba(0,0,0,.25); display: flex;
          align-items: center; justify-content: center; z-index: 900; }
  .fab:hover { background: #256428; }

  /* add-client overlay + modal */
  .overlay { position: fixed; inset: 0; background: rgba(0,0,0,.4);
              display: flex; align-items: center; justify-content: center; z-index: 1500; }
  .overlay[hidden] { display: none; }
  .modal { background: #fff; border-radius: 10px; padding: 24px 28px;
            width: 340px; box-shadow: 0 10px 30px rgba(0,0,0,.2);
            display: flex; flex-direction: column; gap: 14px; }
  .modal h3 { font-size: 15px; font-weight: 700; color: #333; }
  .modal label { display: flex; flex-direction: column; gap: 5px; font-size: 11px;
                  color: #888; text-transform: uppercase; letter-spacing: .04em; }
  .modal input { padding: 7px 9px; border: 1px solid #ddd; border-radius: 5px;
                  font-size: 13px; font-family: inherit; width: 100%; }
  .modal input:focus { outline: none; border-color: #888; }
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
<h1>Clients</h1>
<div class="meta">Généré le {generated_at} — pays au format ISO (FR, BE, ...)</div>

{country_datalist}

<div class="tabs-nav">{tabs_nav}</div>

{tabs_content}

<button id="add-client-fab" class="fab" onclick="return openAddClientModal()" title="Ajouter un client">+</button>

<div id="add-client-overlay" class="overlay" onclick="return onOverlayClick(event)" hidden>
  <div class="modal">
    <h3>Ajouter un client</h3>
    <label>UID
      <input type="text" id="add-client-uid" placeholder="darjeeling">
    </label>
    <label>Nom
      <input type="text" id="add-client-name" placeholder="Darjeeling production">
    </label>
    <label>Adresse
      <input type="text" id="add-client-address-street" placeholder="12-14 rue Jean-Jacques Rousseau">
    </label>
    <label>Ville
      <input type="text" id="add-client-address-city" placeholder="93100 MONTREUIL">
    </label>
    <label>Creditor
      <input type="text" id="add-client-creditor" placeholder="DARJEELING SARL">
    </label>
    <label>Pays
      <input type="text" id="add-client-country" list="country-list" placeholder="FR">
    </label>
    <label>N° TVA
      <input type="text" id="add-client-tva" placeholder="BE1006963829">
    </label>
    <label>Couleur
      <div class="color-cell">
        <input type="color" id="add-client-color-picker" class="color-picker" value="#cccccc" oninput="return syncColorFromPicker(this)">
        <input type="text" id="add-client-color" class="color-input" placeholder="#4e79a7" oninput="return syncColorFromText(this)">
      </div>
    </label>
    <div class="modal-actions">
      <span id="add-client-status" class="add-status"></span>
      <button class="modal-cancel" onclick="return closeAddClientModal()">Annuler</button>
      <button class="modal-submit" onclick="return submitAddClient(this)">Ajouter</button>
    </div>
  </div>
</div>

<script>{RELOAD_SCRIPT}</script>
"""

html = render_shell("Clients", "clients.html", body_content, page_style)

# ─── write ────────────────────────────────────────────────────────────────────

out_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "exports", "view"))
os.makedirs(out_dir, exist_ok=True)
out_path = os.path.join(out_dir, "clients.html")

with open(out_path, "w", encoding="utf-8") as f:
    f.write(html)

print(f"\n── clients ──")
print(f"clients : {len(clients)}")
print(f"\nview @ {out_path}")

if hasattr(os, "startfile") and not configs.webview_mode:
    os.startfile(os.path.normpath(out_path))

if configs.pause_on_exit and not configs.webview_mode: input("\nEntrée pour fermer...")
