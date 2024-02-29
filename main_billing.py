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

db = Database.init_billing()

from packages.export.exporter import *
import modules.system

from modules.path import Path

print("=== EXPORTING BILLS")

for p in db.projects:
    #curProject = db.getProject(p)
    
    print("=== EXPORT BILLS PROJECT : "+p.uid)
    exportBills(p)

if configs.openBillingFolder:
    path = Path.getExportBillingPath()

    print("open folder @ "+path)
    os.startfile(path)

print("done")
exit()