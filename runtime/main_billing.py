"""
    export to html all billing
"""

import locale
try:
    locale.setlocale(locale.LC_ALL, 'fr_FR')
except locale.Error:
    locale.setlocale(locale.LC_ALL, '')

import os
import configs

from packages.database.database import Database

print("\n\nbilling.init.db")
print("===\n\n")

db = Database.init_billing()

from packages.export.exporter import *
from modules.path import Path

qty = len(db.projects)

print("\n\nbilling.solved :     projects x"+str(qty))
print("===\n\n")

for p in db.projects:
    print("\nproject.export :     "+p.uid)
    bills = exportBills(p, configs.billingRange)
    print("project.bills :      x"+str(len(bills)))

if configs.openBillingFolder:
    path = Path.getExportBillingPath()
    print("billing.open.folder @    "+path)
    if hasattr(os, 'startfile'):
        os.startfile(path)

print("done")
exit()
