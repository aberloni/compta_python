"""
Generate exports/view/digital.html — facturation électronique (onglet "Digital").

Bills are sent as Factur-X files to the SUPER PDP plateforme agréée
(modules/superpdp.py, tools/einvoice.py, through app_gui.py):
- "Tester la connexion" → digital_check_connection(): which company the API
  credentials (runtime/superpdp.conf, "Identifiants") belong to, sandbox or
  production.
- per bill: "Vérifier" → digital_check_bill() builds the Factur-X and gets
  the platform's validation report, nothing is sent; "Envoyer" →
  digital_send_bill() does the same then sends it if the report is valid.
- "Rafraîchir les statuts" → digital_refresh_statuses(): latest status of
  every invoice sent (database/digital/superpdp.digital).
The page itself never calls the network: statuses shown are the last ones
recorded.
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

from packages.database.database import Database
from modules import superpdp
from modules.layout import render_shell
from tools.einvoice import load_sent, client_eaddress

# ─── load ─────────────────────────────────────────────────────────────────────

db = Database.init_billing()
sent = load_sent()
configured = superpdp.is_configured()

# ─── helpers ──────────────────────────────────────────────────────────────────

def fmt_eur(v):
    return f"{v:,.2f}&nbsp;€".replace(",", " ")

def th(*cols):
    return "<tr>" + "".join(f"<th>{c}</th>" for c in cols) + "</tr>"

def bill_date(b):
    return datetime.strptime(b.uid, "%Y-%m-%d")

# statuses that mean something went wrong / the buyer said no
BAD_STATUSES = {"api:invalid", "api:rejected", "fr:207", "fr:210", "fr:213", "fr:501"}

def status_cell(fuid):
    s = sent.get(fuid)
    if not s:
        return '<span class="st none">non envoyée</span>'
    cls = "bad" if s["status"] in BAD_STATUSES or s["status"].endswith("error") or s["status"].endswith("rejected") else "ok"
    label = escape(s["status"]) + (f" — {escape(s['status_text'])}" if s["status_text"] else "")
    return (f'<span class="st {cls}">{label}</span>'
            f'<div class="sub">id {escape(s["id"])} · envoyée le {escape(s["sent_at"])}</div>')

def eaddress_cell(client):
    if client is None:
        return '<span class="err">client ?</span>'
    ea = client_eaddress(client)
    if ea is None:
        return (f'<span class="err" title="Ajouter siren: (ou eaddress:schéma:valeur) dans '
                f'clients/{escape(client.uid)}.cli">manquante</span>')
    return f'<span class="mono">{escape(ea[0])}:{escape(ea[1])}</span>'

# ─── one table per year ───────────────────────────────────────────────────────

all_bills = [b for p in db.projects for b in p.bills]
years = sorted({bill_date(b).year for b in all_bills}, reverse=True)

def build_year(year):
    bills = sorted((b for b in all_bills if bill_date(b).year == year), key=lambda b: b.uid, reverse=True)
    rows = ""
    for b in bills:
        fuid = b.getFullUid() or b.uid
        client = b.getClient()
        is_sent = fuid in sent
        send_btn = ('<button class="send-btn" disabled title="Déjà envoyée">Envoyer</button>' if is_sent
                    else '<button class="send-btn" onclick="return sendBill(this)">Envoyer</button>')
        rows += f"""<tr data-project="{b.project.uid}" data-bill="{b.uid}" data-fuid="{escape(fuid)}">
          <td class="mono">{escape(fuid)}</td>
          <td>{b.uid}</td>
          <td>{escape(client.name if client else '?')}</td>
          <td>{escape(b.project.name)}</td>
          <td>{eaddress_cell(client)}</td>
          <td class="num">{fmt_eur(b.getTTC())}</td>
          <td class="status-col">{status_cell(fuid)}</td>
          <td class="actions">
            <button class="check-btn" onclick="return checkBill(this)">Vérifier</button>
            {send_btn}
          </td>
        </tr>
        <tr class="report-row" hidden><td colspan="8"><div class="report"></div></td></tr>"""
    return f"""<table>
      <thead>{th("ID", "Date", "Client", "Projet", "Adresse électronique", "TTC", "Statut SUPER PDP", "")}</thead>
      <tbody>{rows}</tbody>
    </table>"""

years_nav = "".join(
    f'<button class="year-btn {"active" if i == 0 else ""}" id="year-btn-{y}" onclick="showYear({y})">{y}</button>'
    for i, y in enumerate(years))
panels = "".join(
    f'<div class="year-panel {"active" if i == 0 else ""}" id="year-{y}">{build_year(y)}</div>'
    for i, y in enumerate(years)) or '<p class="empty">Aucune facture.</p>'

sent_count = len(sent)
conf_line = ("Identifiants API renseignés." if configured
             else '<span class="err">Identifiants API manquants</span> : cliquer sur « Identifiants » et remplir '
                  '<span class="mono">client_id</span> / <span class="mono">client_secret</span>.')

# ─── assemble ─────────────────────────────────────────────────────────────────

generated_at = datetime.now().strftime("%Y-%m-%d %H:%M")

page_style = """
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { font-family: system-ui, sans-serif; font-size: 14px; background: #f5f5f5; color: #222; }
  h1 { font-size: 20px; font-weight: 700; }
  .meta { color: #888; font-size: 12px; margin: 4px 0 20px; }
  .page-head { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; }
  .page-head .spacer { flex: 1; }
  .pill-btn { padding: 6px 14px; border: 1px solid #ddd; border-radius: 14px; background: #fff;
              cursor: pointer; font-size: 12px; font-weight: 600; color: #333; font-family: inherit; }
  .pill-btn:hover { background: #f0f0f0; }
  .pill-btn:disabled { opacity: .5; cursor: default; }
  .panel { background: #fff; border-radius: 8px; box-shadow: 0 1px 3px rgba(0,0,0,.07);
           padding: 14px 18px; margin-bottom: 20px; font-size: 13px; line-height: 1.6; }
  .panel b { font-weight: 600; }
  #conn-status { margin-left: 6px; }

  .years-nav { display: flex; flex-wrap: wrap; gap: 4px; margin-bottom: 12px; }
  .year-btn { padding: 7px 16px; border: none; border-radius: 6px; background: #e8e8e8;
              cursor: pointer; font-size: 13px; font-weight: 600; color: #555; font-family: inherit; }
  .year-btn:hover { background: #ddd; }
  .year-btn.active { background: #222; color: #fff; }
  .year-panel { display: none; }
  .year-panel.active { display: block; }

  table { width: 100%; border-collapse: collapse; background: #fff; border-radius: 8px; overflow: hidden;
          box-shadow: 0 1px 3px rgba(0,0,0,.07); margin-bottom: 24px; }
  th { background: #f0f0f0; text-align: left; padding: 7px 12px; font-size: 10px;
       text-transform: uppercase; letter-spacing: .05em; color: #888; }
  td { padding: 7px 12px; border-top: 1px solid #f0f0f0; vertical-align: middle; }
  tr:hover td { background: #fafafa; }
  .num { font-variant-numeric: tabular-nums; white-space: nowrap; }
  .mono { font-family: monospace; font-size: 12px; color: #777; }
  .empty { color: #bbb; font-style: italic; }
  .err { color: #c62828; font-weight: 600; }
  .ok-text { color: #2e7d32; font-weight: 600; }
  .st { font-size: 12px; font-weight: 600; }
  .st.none { color: #aaa; font-weight: 400; font-style: italic; }
  .st.ok { color: #2e7d32; }
  .st.bad { color: #c62828; }
  .sub { font-size: 11px; color: #999; }

  .actions { display: flex; gap: 8px; white-space: nowrap; }
  .check-btn { padding: 5px 13px; border: 1px solid #ddd; border-radius: 14px; background: #fff;
               color: #333; cursor: pointer; font-size: 12px; font-weight: 600; }
  .check-btn:hover { background: #f0f0f0; }
  .send-btn { padding: 6px 14px; border: none; border-radius: 14px; background: #3367d6; color: #fff;
              cursor: pointer; font-size: 12px; font-weight: 600; }
  .send-btn:hover { background: #2851ad; }
  .check-btn:disabled, .send-btn:disabled { opacity: .4; cursor: default; }
  .report-row td { background: #fafafa; border-top: none; }
  .report { font-size: 12px; line-height: 1.6; }
  .report ul { margin: 4px 0 0 18px; color: #c62828; }
"""

body_content = f"""
<div class="page-head">
  <h1>Digital — facturation électronique</h1>
  <span class="spacer"></span>
  <button class="pill-btn" onclick="return openFolder()" title="Ouvre exports/digital/, où les fichiers Factur-X sont écrits">Dossier Factur-X</button>
  <button class="pill-btn" onclick="return openConf()" title="Ouvre runtime/superpdp.conf (clé API SUPER PDP, jamais commitée ni sauvegardée)">Identifiants</button>
  <button class="pill-btn" id="refresh-btn" onclick="return refreshStatuses(this)" {"disabled" if not sent_count else ""}>Rafraîchir les statuts</button>
</div>
<div class="meta">Généré le {generated_at} — {sent_count} facture{"s" if sent_count > 1 else ""} envoyée{"s" if sent_count > 1 else ""}</div>

<div class="panel">
  Plateforme agréée : <b>SUPER PDP</b> (<span class="mono">api.superpdp.tech</span>). {conf_line}<br/>
  <button class="pill-btn" onclick="return checkConnection(this)">Tester la connexion</button><span id="conn-status"></span><br/>
  <span class="sub">Le Factur-X (PDF/A-3 + XML CII EN 16931) est produit par l'app ; SUPER PDP sert uniquement à le transmettre.
  « Vérifier » produit le Factur-X et demande le rapport de validation à la plateforme, sans rien envoyer.
  « Envoyer » fait la même chose puis transmet la facture si elle est valide. Une facture envoyée ne peut pas l'être une seconde fois.</span>
</div>

<div class="years-nav">{years_nav}</div>
{panels}

<script>
function api() {{ return window.pywebview && window.pywebview.api; }}
function esc(s) {{ const d = document.createElement('div'); d.textContent = s == null ? '' : String(s); return d.innerHTML; }}

function showYear(y) {{
  document.querySelectorAll('.year-btn').forEach(b => b.classList.toggle('active', b.id === 'year-btn-' + y));
  document.querySelectorAll('.year-panel').forEach(p => p.classList.toggle('active', p.id === 'year-' + y));
  try {{ sessionStorage.setItem('digital::year', String(y)); }} catch (e) {{}}
}}
(function () {{
  let y = null;
  try {{ y = sessionStorage.getItem('digital::year'); }} catch (e) {{}}
  if (y && document.getElementById('year-' + y)) showYear(y);
}})();

async function reloadPage() {{
  document.body.style.cursor = 'wait';
  try {{ await api().run('digital.html'); }} catch (e) {{}}
  window.location.reload();
}}

function showReport(row, html) {{
  const rr = row.nextElementSibling;
  rr.hidden = false;
  rr.querySelector('.report').innerHTML = html;
}}

function reportHtml(r) {{
  if (!r.ok) {{
    let h = '<span class="err">' + esc(r.error || 'Erreur') + '</span>';
    if (r.failures && r.failures.length) h += '<ul>' + r.failures.map(f => '<li>' + esc(f) + '</li>').join('') + '</ul>';
    return h;
  }}
  if (r.valid === null || r.valid === undefined) {{
    return '<span class="ok-text">' + esc(r.note || 'Factur-X généré') + '</span> <span class="mono">' + esc(r.path) + '</span>';
  }}
  if (r.valid === false) {{
    return '<span class="err">Factur-X non valide</span> (' + esc(r.path) + ')<ul>'
      + (r.failures || []).map(f => '<li>' + esc(f) + '</li>').join('') + '</ul>';
  }}
  return '<span class="ok-text">Factur-X valide ✓</span> <span class="mono">' + esc(r.path) + '</span>';
}}

async function checkBill(btn) {{
  const row = btn.closest('tr');
  if (!api()) {{ showReport(row, "Indisponible en dehors de l'application."); return false; }}
  btn.disabled = true; document.body.style.cursor = 'wait';
  showReport(row, 'Vérification en cours…');
  let r;
  try {{ r = await api().digital_check_bill(row.dataset.project, row.dataset.bill); }}
  catch (e) {{ r = {{ ok: false, error: String(e) }}; }}
  btn.disabled = false; document.body.style.cursor = '';
  showReport(row, reportHtml(r));
  return false;
}}

async function sendBill(btn) {{
  const row = btn.closest('tr');
  if (!api()) {{ showReport(row, "Indisponible en dehors de l'application."); return false; }}
  if (!confirm('Envoyer la facture ' + row.dataset.fuid + ' au client via SUPER PDP ?\\n\\nL\\'envoi est définitif.')) return false;
  btn.disabled = true; document.body.style.cursor = 'wait';
  showReport(row, 'Envoi en cours…');
  let r;
  try {{ r = await api().digital_send_bill(row.dataset.project, row.dataset.bill); }}
  catch (e) {{ r = {{ ok: false, error: String(e) }}; }}
  document.body.style.cursor = '';
  if (r.ok) {{ await reloadPage(); return false; }}
  btn.disabled = false;
  showReport(row, reportHtml(r));
  return false;
}}

async function refreshStatuses(btn) {{
  if (!api()) return false;
  btn.disabled = true; document.body.style.cursor = 'wait';
  let r;
  try {{ r = await api().digital_refresh_statuses(); }} catch (e) {{ r = {{ ok: false, error: String(e) }}; }}
  if (!r.ok) {{ alert('Erreur : ' + r.error); btn.disabled = false; document.body.style.cursor = ''; return false; }}
  if (r.errors && r.errors.length) alert('Statut indisponible pour :\\n' + r.errors.join('\\n'));
  await reloadPage();
  return false;
}}

async function checkConnection(btn) {{
  const out = document.getElementById('conn-status');
  if (!api()) {{ out.textContent = " Indisponible en dehors de l'application."; return false; }}
  btn.disabled = true; out.textContent = ' …';
  let r;
  try {{ r = await api().digital_check_connection(); }} catch (e) {{ r = {{ ok: false, error: String(e) }}; }}
  btn.disabled = false;
  out.innerHTML = r.ok
    ? ' <span class="ok-text">✓ ' + esc(r.name) + '</span> <span class="mono">' + esc(r.number) + '</span> — '
      + (r.env === 'production' ? '<b>production</b>' : '<b>sandbox</b> (test)')
    : ' <span class="err">' + esc(r.error) + '</span>';
  return false;
}}

function openConf() {{ if (api()) api().digital_open_conf(); return false; }}
function openFolder() {{ if (api()) api().digital_open_folder(); return false; }}
</script>
"""

html = render_shell("Digital", "digital.html", body_content, page_style)

# ─── write ────────────────────────────────────────────────────────────────────

out_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "exports", "view"))
os.makedirs(out_dir, exist_ok=True)
out_path = os.path.join(out_dir, "digital.html")

with open(out_path, "w", encoding="utf-8") as f:
    f.write(html)

print(f"\n── digital ──")
print(f"factures : {len(all_bills)}")
print(f"envoyées : {sent_count}")
print(f"api      : {'configurée' if configured else 'identifiants manquants'}")
print(f"\nview @ {out_path}")

if hasattr(os, "startfile") and not configs.webview_mode:
    os.startfile(os.path.normpath(out_path))

if configs.pause_on_exit and not configs.webview_mode: input("\nEntrée pour fermer...")
