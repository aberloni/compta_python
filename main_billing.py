"""
    export html files of bills
"""

import locale
locale.setlocale(locale.LC_ALL, 'fr_FR')

# DATABASE LOADER

import os
import configs

from library.database import Database

# loading DB

db = Database.billing()

import library.exporter
import library.system
from library.path import Path

print("=== EXPORTING BILLS")

for p in db.projects:
    #curProject = db.getProject(p)
    
    print(" === EXPORT === > "+p.uid)
    library.exporter.exportBills(p)

if configs.openBillingFolder:
    path = Path.getExportBillingPath()

    print("open folder @ "+path)
    os.startfile(path)

print("done")
exit()