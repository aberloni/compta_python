"""
    export to html all billing
"""

import locale
try:
    locale.setlocale(locale.LC_ALL, 'fr_FR')
except locale.Error:
    locale.setlocale(locale.LC_ALL, '')

import os
from datetime import datetime
import configs

from packages.database.database import Database

print("\n\nbilling.init.db")
print("===\n\n")

db = Database.init_billing()

from packages.export.exporter import *
from modules.path import Path

# clear previous exports before regenerating
billingPath = Path.getExportBillingPath()
os.makedirs(billingPath, exist_ok=True)
for f in os.listdir(billingPath):
    if f.endswith((".html", ".pdf", ".dump")):
        os.remove(os.path.join(billingPath, f))

qty = len(db.projects)

print("\n\nbilling.solved :     projects x"+str(qty))
print("===\n\n")

all_bills = []

for p in db.projects:
    print("\nproject.export :     "+p.uid)
    bills = exportBills(p, configs.billingRange)
    print("project.bills :      x"+str(len(bills)))
    for b in bills:
        all_bills.append((p, b))

all_bills.sort(key=lambda x: x[1].uid)

# run dump
exportPath = Path.getExportBillingPath()
dumpPath = exportPath + "_run.dump"

with open(dumpPath, "w", encoding="utf-8") as f:

    f.write(f"# Billing run — {datetime.now().strftime('%Y-%m-%d %H:%M')}\n")
    f.write(f"# Range : {configs.billingRange[0]} → {configs.billingRange[1]}\n")
    f.write(f"# Bills generated : {len(all_bills)}\n")
    f.write("\n")

    for project, bill in all_bills:
        client = bill.getClient()
        fuid = bill.getFullUid()
        ht = bill.getHT()
        tva = bill.getTvaTotal()
        ttc = bill.getTTC()
        days = bill.countDays()

        f.write(f"---\n")
        f.write(f"bill      {fuid}\n")
        f.write(f"date      {bill.uid}\n")
        f.write(f"period    {bill.start:%Y-%m-%d} → {bill.end:%Y-%m-%d}\n")
        f.write(f"project   {project.name} ({project.uid})\n")
        f.write(f"client    {client.name} ({client.uid})\n")
        taux_range = project.getTauxRange(bill.start, bill.end)
        taux_str = " → ".join(str(t) for t in taux_range) + " €/j"
        f.write(f"days      {days}\n")
        f.write(f"taux      {taux_str}\n")
        f.write(f"HT        {ht} €\n")
        f.write(f"TVA       {tva} €\n")
        f.write(f"TTC       {ttc} €\n")

        if bill.hasTransactions():
            for t in bill.transactions:
                f.write(f"  + {t.label}  x{t.quantity}  {t.solvePrice()} €\n")

        f.write("\n")

print(f"dump @ {dumpPath}")

if configs.openBillingFolder:
    path = Path.getExportBillingPath()
    print("billing.open.folder @    "+path)
    if hasattr(os, 'startfile'):
        os.startfile(path)

print("done")
exit()
