"""
Generate exports/view/backups.html — import / export de la base (zip).

- "Exporter…" zips database/ to a location picked in a save dialog
  (app_gui.py's export_database()).
- "Importer…" picks any zip and replaces database/ with it
  (import_database()); the current database is zipped to exports/backups/
  first, see do_zip_restore.restore_zip().
- "Dossiers d'export": one group per kind of export (modules/export_folders.py),
  each with its local folder, always written to, plus extra folders (cloud
  sync, USB key, ...) added or removed per group (add_export_folder() /
  remove_export_folder()) that every new export of that kind is copied to:
    zip  exports/backups/   "Sauvegarder maintenant" / "Créer une sauvegarde"
                            (backup_database())
    pdf  exports/billings/  every bill PDF generated (packages/export/exporter.py)
- The table lists the backup zips found in every "zip" folder, each with a
  "Restaurer" button (restore_backup()). exports/backups/ ("Créer une
  sauvegarde", backupBeforeBilling, and pre-import safety backups all land
  there) is always listed. In extra folders only zips that are actual
  database backups are shown, other zips are skipped.
- "Dernière sauvegarde" = the last zip saved, exported or imported, i.e. what
  the data now on disk is based on, and the list of files modified since
  (= modifications still to be saved) -- see modules/backup_state.py. The
  same "Dernière sauvegarde" line is in every page's footer.
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
from html import escape

import configs
from do_zip_backup import SOURCE_DIR, KEEP
from do_zip_restore import folder_label, list_backups
from modules import backup_state, export_folders
from modules.layout import render_shell

# ─── helpers ──────────────────────────────────────────────────────────────────

def fmt_size(n_bytes):
    return f"{n_bytes / 1024:.1f} ko"

# ─── current database ─────────────────────────────────────────────────────────

db_files, db_bytes = 0, 0
for dirpath, _, filenames in os.walk(SOURCE_DIR):
    for fname in filenames:
        db_files += 1
        db_bytes += os.path.getsize(os.path.join(dirpath, fname))

# ─── modifications since the last saved / exported / imported zip ─────────────

base = backup_state.baseline()
latest_text = backup_state.summary_text(base)

CHANGE_KINDS = [("modified", "modifié"), ("added", "ajouté"), ("removed", "supprimé")]

def changes_block():
    save_btn = '<button class="main-btn" onclick="return createBackup(this)">Sauvegarder maintenant</button>'
    if base is None:
        return f'''<div class="changes pending"><div class="changes-head">
      <b>● Aucune sauvegarde</b> — toute la base reste à sauvegarder. {save_btn}</div></div>'''
    changes = backup_state.pending_changes(base)
    total = sum(len(names) for names in changes.values())
    if total == 0:
        return '<div class="changes clean"><b>✓ Aucune modification</b> depuis cette sauvegarde.</div>'
    counts = ", ".join(f"{len(changes[k])} {label}{'s' if len(changes[k]) > 1 else ''}"
                       for k, label in CHANGE_KINDS if changes[k])
    items = "".join(f'<li><span class="chg {k}">{label}</span> <span class="mono">{escape(name)}</span></li>'
                    for k, label in CHANGE_KINDS for name in changes[k])
    return f'''<div class="changes pending">
      <div class="changes-head"><b>● {total} fichier{"s" if total > 1 else ""} à sauvegarder</b> ({counts}) {save_btn}</div>
      <details><summary>Voir les fichiers</summary><ul>{items}</ul></details>
    </div>'''

guessed_note = ('<div class="meta-note">Déduite de la sauvegarde la plus récente : le suivi exact des '
                'modifications commence à la prochaine sauvegarde, export ou import.</div>'
                if base and base["guessed"] else "")

# ─── export folders (one group per kind of export) ─────────────────────────────

backups = list_backups()

zips_per_folder = {}
for b in backups:
    zips_per_folder[b.folder] = zips_per_folder.get(b.folder, 0) + 1

GROUP_NOTES = {
    "zip": "Copiées à chaque « Sauvegarder ». Les sauvegardes trouvées dans ces dossiers sont listées plus bas, prêtes à restaurer.",
    "pdf": "Copiées à chaque génération d'une facture (bouton PDF de « Éditer factures », facturation complète).",
}

def folder_info(group, path, is_local):
    if group == "zip" and is_local:
        return f"local — les {KEEP} plus récentes sont conservées"
    if not os.path.isdir(path):
        return "local — vide" if is_local else '<span class="err">introuvable (clé débranchée ?)</span>'
    if group == "zip":
        count = f"{zips_per_folder.get(path, 0)} sauvegarde(s)"
    else:
        count = f"{sum(1 for n in os.listdir(path) if n.lower().endswith('.pdf'))} PDF"
    return f"local — {count}" if is_local else count

def folder_row(group, path, is_local):
    remove_btn = "" if is_local else \
        '<button class="small-btn" onclick="return removeFolder(this)" title="Retire le dossier de la liste, sans toucher à son contenu">Retirer</button>'
    return f"""<div class="folder-row" data-folder="{escape(path)}">
      <span class="mono folder-path">{escape(path)}</span>
      <span class="folder-info">{folder_info(group, path, is_local)}</span>
      <button class="small-btn" onclick="return openFolder(this)">Ouvrir</button>
      {remove_btn}
    </div>"""

extra_folders = export_folders.load_all()

def group_block(group):
    label, local = export_folders.GROUPS[group]
    rows = [(local, True)] + [(f, False) for f in extra_folders[group]]
    rows_html = "".join(folder_row(group, path, is_local) for path, is_local in rows)
    return f"""<div class="folder-group" data-group="{group}">
  <div class="section-head">
    <h3>{escape(label)}</h3>
    <span class="spacer"></span>
    <button class="small-btn" onclick="return addFolder(this)">Ajouter un dossier…</button>
  </div>
  <div class="group-note">{escape(GROUP_NOTES[group])}</div>
  <div class="folders">{rows_html}</div>
  <span class="status folders-status"></span>
</div>"""

groups_html = "".join(group_block(g) for g in export_folders.GROUPS)

def backup_row(folder, is_local, name, date, count, size, uid):
    count_cell = str(count) if count is not None else '<span class="err">zip invalide</span>'
    disabled = " disabled" if count is None else ""
    created = date.strftime("%Y-%m-%d %H:%M:%S")
    if uid:
        uid_cell, date_cell = escape(uid), created
    else:
        # zip made before uids: no uid, date guessed from its name / mtime
        uid_cell = '<span class="empty" title="sauvegarde antérieure aux uid">—</span>'
        date_cell = f'<span class="guessed" title="date déduite du nom du fichier">{created}</span>'
    return f"""<tr data-folder="{escape(folder)}" data-name="{escape(name)}" data-uid="{escape(uid or '')}" data-created="{created if uid else ''}">
      <td class="mono">{uid_cell}</td>
      <td>{date_cell}</td>
      <td title="{escape(folder)}">{escape(folder_label(folder, is_local))}</td>
      <td class="mono">{escape(name)}</td>
      <td class="num">{count_cell}</td>
      <td class="num">{fmt_size(size)}</td>
      <td class="row-actions"><button class="small-btn" onclick="return restoreBackup(this)"{disabled}>Restaurer</button></td>
    </tr>"""

if backups:
    rows_html = "".join(backup_row(*b) for b in backups)
else:
    rows_html = '<tr><td colspan="7" class="empty">Aucune sauvegarde</td></tr>'

# ─── assemble ─────────────────────────────────────────────────────────────────

generated_at = datetime.now().strftime("%Y-%m-%d %H:%M")

PAGE_SCRIPT = """
const FLASH_KEY = 'backups-flash';

function hasApi(statusEl) {
  if (window.pywebview && window.pywebview.api) return true;
  setStatus(statusEl, "Indisponible en dehors de l'application.", 'err');
  return false;
}

function setStatus(el, text, kind) {
  el.textContent = text;
  el.className = 'status' + (kind ? ' ' + kind : '');
}

// message shown again after the page regenerates itself (see reloadWithFlash)
function showFlash() {
  let flash = null;
  try { flash = JSON.parse(sessionStorage.getItem(FLASH_KEY)); sessionStorage.removeItem(FLASH_KEY); } catch (e) {}
  if (flash) setStatus(document.getElementById('flash-status'), flash.text, flash.kind);
}

async function reloadWithFlash(text, kind) {
  try { sessionStorage.setItem(FLASH_KEY, JSON.stringify({ text: text, kind: kind })); } catch (e) {}
  document.body.style.cursor = 'wait';
  try { await window.pywebview.api.run('backups.html'); } catch (e) {}
  window.location.reload();
}

// " (uid a1b2c3d4, créée le 2026-10-03 14:22:05)", or "" for zips made before uids existed
function uidSuffix(uid, created) {
  if (!uid) return '';
  return ' (uid ' + uid + (created ? ', créée le ' + created : '') + ')';
}

function restoredMessage(result) {
  let msg = 'Base remplacée par la sauvegarde' + uidSuffix(result.uid, result.created) + ', ' + result.files + ' fichiers.';
  if (result.safety_backup) msg += ' Ancienne base sauvegardée : ' + result.safety_backup.split(/[\\\\/]/).pop();
  return msg;
}

async function exportDatabase(btn) {
  const status = document.getElementById('export-status');
  if (!hasApi(status)) return false;
  btn.disabled = true;
  setStatus(status, '');
  const result = await window.pywebview.api.export_database();
  btn.disabled = false;
  if (result && result.ok) {
    await reloadWithFlash('Exporté ✓ ' + result.path + ' (' + result.files + ' fichiers, uid ' + result.uid + ', créée le ' + result.created + ')', 'ok');
  } else if (result && result.cancelled) {
    setStatus(status, '');
  } else {
    setStatus(status, 'Erreur : ' + (result && result.error || '?'), 'err');
  }
  return false;
}

async function importDatabase(btn) {
  const status = document.getElementById('import-status');
  if (!hasApi(status)) return false;
  btn.disabled = true;
  setStatus(status, '');
  const picked = await window.pywebview.api.pick_import_file();
  if (!picked || picked.cancelled) { btn.disabled = false; return false; }
  if (!picked.ok) {
    btn.disabled = false;
    setStatus(status, 'Erreur : ' + (picked.error || '?'), 'err');
    return false;
  }
  if (!confirm('Remplacer toute la base par « ' + picked.name + ' »' + uidSuffix(picked.uid, picked.created) + ', ' + picked.files + ' fichiers ?\\n\\n'
             + 'La base actuelle sera d\\'abord sauvegardée dans exports/backups/.')) {
    btn.disabled = false;
    return false;
  }
  const result = await window.pywebview.api.import_database(picked.path);
  btn.disabled = false;
  if (result && result.ok) {
    await reloadWithFlash(restoredMessage(result), 'ok');
  } else {
    setStatus(status, 'Erreur : ' + (result && result.error || '?'), 'err');
  }
  return false;
}

async function restoreBackup(btn) {
  const status = document.getElementById('flash-status');
  if (!hasApi(status)) return false;
  const row = btn.closest('tr');
  const folder = row.dataset.folder, name = row.dataset.name;
  if (!confirm('Remplacer toute la base par la sauvegarde « ' + name + ' »' + uidSuffix(row.dataset.uid, row.dataset.created) + ' ?\\n(' + folder + ')\\n\\n'
             + 'La base actuelle sera d\\'abord sauvegardée dans exports/backups/.')) {
    return false;
  }
  btn.disabled = true;
  const result = await window.pywebview.api.restore_backup(folder, name);
  btn.disabled = false;
  if (result && result.ok) {
    await reloadWithFlash(restoredMessage(result), 'ok');
  } else {
    setStatus(status, 'Erreur : ' + (result && result.error || '?'), 'err');
  }
  return false;
}

async function createBackup(btn) {
  const status = document.getElementById('flash-status');
  if (!hasApi(status)) return false;
  btn.disabled = true;
  const result = await window.pywebview.api.backup_database();
  btn.disabled = false;
  if (result && result.ok) {
    let msg = 'Sauvegarde créée : ' + result.path.split(/[\\\\/]/).pop();
    const copied = (result.copied || []).length, failed = result.failed || [];
    if (copied + failed.length) msg += ', copiée dans ' + copied + '/' + (copied + failed.length) + ' dossier(s)';
    if (failed.length) msg += ' — échec : ' + failed.map(f => f.folder + ' (' + f.error + ')').join(', ');
    await reloadWithFlash(msg, failed.length ? 'err' : 'ok');
  } else {
    setStatus(status, 'Erreur : ' + (result && result.error || '?'), 'err');
  }
  return false;
}

// group block of a folder row / button: its group key, label, and status line
function folderGroup(btn) {
  const block = btn.closest('.folder-group');
  return { key: block.dataset.group, label: block.querySelector('h3').textContent,
           status: block.querySelector('.folders-status') };
}

function openFolder(btn) {
  const folder = btn.closest('.folder-row').dataset.folder;
  if (window.pywebview && window.pywebview.api) window.pywebview.api.open_export_folder(folderGroup(btn).key, folder);
  return false;
}

async function addFolder(btn) {
  const group = folderGroup(btn), status = group.status;
  if (!hasApi(status)) return false;
  btn.disabled = true;
  setStatus(status, '');
  const result = await window.pywebview.api.add_export_folder(group.key);
  btn.disabled = false;
  if (result && result.ok) {
    await reloadWithFlash('Dossier ajouté (' + group.label + ') : ' + result.path, 'ok');
  } else if (!(result && result.cancelled)) {
    setStatus(status, 'Erreur : ' + (result && result.error || '?'), 'err');
  }
  return false;
}

async function removeFolder(btn) {
  const group = folderGroup(btn), status = group.status;
  if (!hasApi(status)) return false;
  const folder = btn.closest('.folder-row').dataset.folder;
  btn.disabled = true;
  const result = await window.pywebview.api.remove_export_folder(group.key, folder);
  btn.disabled = false;
  if (result && result.ok) {
    await reloadWithFlash('Dossier retiré de la liste (' + group.label + ') : ' + folder, 'ok');
  } else {
    setStatus(status, 'Erreur : ' + (result && result.error || '?'), 'err');
  }
  return false;
}

showFlash();
"""

page_style = """
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { font-family: system-ui, sans-serif; font-size: 14px; background: #f5f5f5; color: #222; }
  h1 { font-size: 20px; font-weight: 700; margin-bottom: 4px; }
  h2 { font-size: 15px; font-weight: 700; margin-bottom: 6px; }
  h3 { font-size: 13px; font-weight: 700; }
  .meta { color: #888; font-size: 12px; margin-bottom: 24px; }
  .latest { font-size: 13px; color: #555; margin-bottom: 4px; }
  .meta-note { font-size: 11px; color: #999; font-style: italic; margin-bottom: 4px; }

  .changes { border-radius: 8px; padding: 12px 16px; margin: 8px 0 12px; max-width: 760px; font-size: 13px; }
  .changes.clean { background: #e8f5e9; color: #2e7d32; }
  .changes.pending { background: #fff3e0; color: #8a4b00; }
  .changes-head { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; }
  .changes-head .main-btn { margin-left: auto; }
  .changes details { margin-top: 8px; }
  .changes summary { cursor: pointer; font-size: 12px; }
  .changes ul { list-style: none; margin-top: 6px; max-height: 240px; overflow-y: auto; }
  .changes li { padding: 2px 0; }
  .chg { display: inline-block; min-width: 64px; font-size: 11px; font-weight: 600; }
  .chg.added { color: #2e7d32; }
  .chg.removed { color: #c62828; }

  .mono { font-family: monospace; font-size: 12px; color: #555; }
  .empty { color: #bbb; font-style: italic; }
  .err { color: #c62828; }
  .guessed { color: #999; font-style: italic; }

  .action-cards { display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
                  gap: 14px; margin-bottom: 32px; max-width: 760px; }
  .action-card { background: #fff; border-radius: 8px; padding: 20px 22px;
                 box-shadow: 0 1px 3px rgba(0,0,0,.07); display: flex; flex-direction: column; gap: 12px; }
  .action-card p { font-size: 12px; color: #888; line-height: 1.5; flex: 1; }

  .main-btn { align-self: flex-start; padding: 7px 16px; border: none; border-radius: 16px;
              background: #222; color: #fff; cursor: pointer; font-size: 13px; font-weight: 600; }
  .main-btn:hover { background: #444; }
  .main-btn.danger { background: #c62828; }
  .main-btn.danger:hover { background: #a42020; }
  .main-btn:disabled, .small-btn:disabled { opacity: .5; cursor: default; }

  .status { font-size: 12px; word-break: break-all; }
  .status.ok { color: #2e7d32; font-weight: 600; }
  .status.err { color: #c62828; font-weight: 600; }
  #flash-status { display: block; margin-bottom: 24px; }
  .folders-status { display: block; }
  .folder-group { margin-bottom: 18px; max-width: 900px; }
  .group-note { font-size: 12px; color: #888; }
  .export-folders { margin-bottom: 32px; }

  .folders { background: #fff; border-radius: 8px; box-shadow: 0 1px 3px rgba(0,0,0,.07);
             margin: 8px 0 8px; max-width: 900px; }
  .folder-row { display: flex; align-items: center; gap: 10px; padding: 9px 14px;
                border-bottom: 1px solid #f3f3f3; }
  .folder-row:last-child { border-bottom: none; }
  .folder-path { flex: 1; min-width: 0; overflow-wrap: anywhere; }
  .folder-info { font-size: 12px; color: #888; white-space: nowrap; }

  .section-head { display: flex; align-items: baseline; gap: 12px; margin-bottom: 4px; }
  .section-head .spacer { flex: 1; }
  .small-btn { padding: 4px 12px; border: 1px solid #ddd; border-radius: 12px; background: #fff;
               cursor: pointer; font-size: 12px; color: #333; }
  .small-btn:hover { background: #f0f0f0; }

  table { border-collapse: collapse; background: #fff; border-radius: 8px; overflow: hidden;
          box-shadow: 0 1px 3px rgba(0,0,0,.07); min-width: 600px; }
  th { text-align: left; font-size: 11px; color: #888; text-transform: uppercase; letter-spacing: .04em;
       padding: 10px 14px; border-bottom: 1px solid #eee; font-weight: 600; }
  td { padding: 8px 14px; border-bottom: 1px solid #f3f3f3; font-size: 13px; }
  tr:last-child td { border-bottom: none; }
  td.num { text-align: right; font-variant-numeric: tabular-nums; }
  td.row-actions { text-align: right; }
"""

body_content = f"""
<h1>Sauvegarde</h1>
<div class="meta">Généré le {generated_at} — base actuelle : {db_files} fichiers, {fmt_size(db_bytes)}</div>

<div class="latest">Dernière sauvegarde : <b>{escape(latest_text)}</b></div>
{guessed_note}
{changes_block()}
<span id="flash-status" class="status"></span>

<div class="action-cards">
  <div class="action-card">
    <h2>Exporter</h2>
    <p>Enregistre toute la base (dossier database/) dans un zip, à l'emplacement de ton choix — clé USB, cloud, autre machine…</p>
    <button class="main-btn" onclick="return exportDatabase(this)">Exporter…</button>
    <span id="export-status" class="status"></span>
  </div>
  <div class="action-card">
    <h2>Importer</h2>
    <p>Remplace <b>toute</b> la base par le contenu d'un zip exporté. La base actuelle est d'abord sauvegardée dans la liste ci-dessous, pour pouvoir revenir en arrière.</p>
    <button class="main-btn danger" onclick="return importDatabase(this)">Importer…</button>
    <span id="import-status" class="status"></span>
  </div>
</div>

<div class="export-folders">
  <h2>Dossiers d'export</h2>
  <div class="meta-note">Chaque export est toujours écrit dans son dossier local, puis copié dans les autres dossiers de son groupe.</div>
  {groups_html}
</div>

<div class="section-head">
  <h2>Sauvegardes</h2>
  <span class="spacer"></span>
  <button class="small-btn" onclick="return createBackup(this)" title="Crée un zip dans le dossier local et le copie dans les autres dossiers">Créer une sauvegarde</button>
</div>

<table data-default-sort="1:desc">
  <thead><tr><th>UID</th><th>Créée le</th><th>Dossier</th><th>Fichier</th><th>Fichiers</th><th>Taille</th><th></th></tr></thead>
  <tbody>{rows_html}</tbody>
</table>

<script>{PAGE_SCRIPT}</script>
"""

html = render_shell("Sauvegarde", "backups.html", body_content, page_style)

# ─── write ────────────────────────────────────────────────────────────────────

out_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "exports", "view"))
os.makedirs(out_dir, exist_ok=True)
out_path = os.path.join(out_dir, "backups.html")

with open(out_path, "w", encoding="utf-8") as f:
    f.write(html)

print(f"\n── backups ──")
print(f"base     : {db_files} fichiers")
print(f"zips     : {len(backups)}")
print(f"dernière : {latest_text}")
print(f"\nview @ {out_path}")

if hasattr(os, "startfile") and not configs.webview_mode:
    os.startfile(os.path.normpath(out_path))

if configs.pause_on_exit and not configs.webview_mode: input("\nEntrée pour fermer...")
