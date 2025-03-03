"""
    export to html all billing
"""

import locale
locale.setlocale(locale.LC_ALL, 'fr_FR')

# DATABASE LOADER

import os
import configs

from packages.database.database import Database

# loading DB

print("\n\nbilling.init.db")
print("===\n\n")

db = Database.init_billing()

from packages.export.exporter import *
from modules.path import Path

qty = len(db.projects)

print("\n\nbilling.solved :     projects x"+str(qty))
print("===\n\n")

for p in db.projects:
    #curProject = db.getProject(p)
    
    print("\n\nproject.export :     "+p.uid)

    exportBills(p, configs.billingYears)

if configs.openBillingFolder:
    path = Path.getExportBillingPath()

    print("billing.open.folder @    "+path)
    
    os.startfile(path)

print("done")
exit()
