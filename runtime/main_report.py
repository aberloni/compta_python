"""
    generate _report.html in exports/billings/
    open it after generation
"""

import locale
try:
    locale.setlocale(locale.LC_ALL, 'fr_FR')
except locale.Error:
    locale.setlocale(locale.LC_ALL, '')

import os
import json
import configs

from packages.database.database import Database
from modules.path import Path

db = Database.init_billing()

bills = []
total_ht = 0
total_tva = 0
total_ttc = 0

for p in db.projects:
    for b in p.bills:
        fuid = b.getFullUid()
        if fuid is None:
            continue
        ht = round(b.getHT(), 2)
        tva = round(b.getTvaTotal(), 2)
        ttc = round(b.getTTC(), 2)
        total_ht += ht
        total_tva += tva
        total_ttc += ttc
        bills.append({
            'uid': fuid,
            'date': b.uid,
            'project': p.name,
            'project_uid': p.uid,
            'client': p.client.name if p.client else '?',
            'period': b.start.strftime('%d/%m/%Y') + ' → ' + b.end.strftime('%d/%m/%Y'),
            'days': b.countDays(),
            'ht': ht,
            'tva': tva,
            'ttc': ttc,
        })

bills_json = json.dumps(bills, ensure_ascii=False)

html = f"""<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<title>Rapport de facturation</title>
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ font-family: Arial, sans-serif; font-size: 13px; background: #f5f5f5; color: #111; padding: 2rem; }}
  h1 {{ font-size: 20px; font-weight: 600; margin-bottom: 1.5rem; }}
  .metrics {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; margin-bottom: 1.5rem; }}
  .metric {{ background: #fff; border: 1px solid #e0e0e0; border-radius: 8px; padding: 14px 16px; }}
  .metric-label {{ font-size: 11px; color: #888; text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 6px; }}
  .metric-value {{ font-size: 22px; font-weight: 600; }}
  .card {{ background: #fff; border: 1px solid #e0e0e0; border-radius: 8px; overflow: hidden; }}
  table {{ width: 100%; border-collapse: collapse; }}
  thead th {{ font-size: 11px; font-weight: 600; color: #888; text-transform: uppercase; letter-spacing: 0.05em; padding: 10px 12px; border-bottom: 1px solid #e0e0e0; text-align: left; }}
  tbody td {{ padding: 10px 12px; border-bottom: 1px solid #f0f0f0; }}
  tbody tr:last-child td {{ border-bottom: none; }}
  tbody tr:hover td {{ background: #fafafa; }}
  .num {{ text-align: right; font-variant-numeric: tabular-nums; }}
  .uid {{ font-family: monospace; font-size: 12px; color: #555; }}
  .badge {{ display: inline-block; font-size: 11px; padding: 2px 8px; border-radius: 100px; font-weight: 500; }}
  .link {{ font-size: 11px; color: #1a73e8; text-decoration: none; }}
  .link:hover {{ text-decoration: underline; }}
  tfoot td {{ padding: 10px 12px; font-weight: 600; border-top: 2px solid #e0e0e0; background: #fafafa; }}
  .generated {{ font-size: 11px; color: #aaa; margin-top: 1rem; }}
</style>
</head>
<body>

<h1>Rapport de facturation</h1>

<div class="metrics">
  <div class="metric">
    <div class="metric-label">Factures</div>
    <div class="metric-value">{len(bills)}</div>
  </div>
  <div class="metric">
    <div class="metric-label">Total HT</div>
    <div class="metric-value">{round(total_ht):,} €</div>
  </div>
  <div class="metric">
    <div class="metric-label">TVA</div>
    <div class="metric-value">{round(total_tva):,} €</div>
  </div>
  <div class="metric">
    <div class="metric-label">Total TTC</div>
    <div class="metric-value">{round(total_ttc):,} €</div>
  </div>
</div>

<div class="card">
<table>
  <thead>
    <tr>
      <th>N° facture</th>
      <th>Client</th>
      <th>Période</th>
      <th class="num">Jours</th>
      <th class="num">HT</th>
      <th class="num">TVA</th>
      <th class="num">TTC</th>
      <th></th>
    </tr>
  </thead>
  <tbody>
"""

colors = ['#e8e4ff', '#ffe8e0', '#e0f4ee', '#e0eeff', '#fff0e0']
text_colors = ['#4a3d99', '#8a3010', '#0a5a3a', '#0a3a7a', '#7a4a0a']

project_uids = list(dict.fromkeys(b['project_uid'] for b in bills))
color_map = {uid: (colors[i % len(colors)], text_colors[i % len(text_colors)]) for i, uid in enumerate(project_uids)}

export_path = Path.getExportBillingPath()

for b in bills:
    bg, fc = color_map[b['project_uid']]
    badge = f'<span class="badge" style="background:{bg};color:{fc}">{b["project_uid"]}</span>'
    pdf_file = b['uid'] + '_' + b['client_uid'] if 'client_uid' in b else b['uid']
    # find matching pdf
    pdf_name = b['uid'] + '_' + b['project_uid'] + '_' + b['project_uid'] + '.pdf'
    pdf_path = export_path + pdf_name
    pdf_link = f'<a class="link" href="{pdf_path}">PDF</a>' if os.path.exists(pdf_path) else ''
    days_str = str(int(b['days'])) if b['days'] == int(b['days']) else str(b['days'])
    html += f"""    <tr>
      <td><span class="uid">{b['uid']}</span></td>
      <td>{badge}</td>
      <td>{b['period']}</td>
      <td class="num">{days_str}</td>
      <td class="num">{b['ht']:,.0f} €</td>
      <td class="num">{b['tva']:,.0f} €</td>
      <td class="num"><strong>{b['ttc']:,.0f} €</strong></td>
      <td class="num">{pdf_link}</td>
    </tr>
"""

html += f"""  </tbody>
  <tfoot>
    <tr>
      <td colspan="4">Total</td>
      <td class="num">{round(total_ht):,} €</td>
      <td class="num">{round(total_tva):,} €</td>
      <td class="num">{round(total_ttc):,} €</td>
      <td></td>
    </tr>
  </tfoot>
</table>
</div>

<p class="generated">Généré le {__import__('datetime').datetime.now().strftime('%d/%m/%Y à %H:%M')}</p>

</body>
</html>"""

report_path = export_path + "_report.html"
with open(report_path, "w", encoding="utf-8") as f:
    f.write(html)

print("report generated @ " + report_path)

if hasattr(os, 'startfile'):
    os.startfile(report_path)

