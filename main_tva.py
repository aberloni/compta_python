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

if len(db.projects) <= 0:
    print("no project ?")
    exit()

for p in db.projects:
    bills = p.getBills()

    if len(bills) <= 0:
        print("no billing ?")

    for b in bills:

        ht = b.getHT()
        ttc = b.getTTC()
        tva = b.getTvaTotal()

        print(b.getBillFullUid()+" >> HT : "+str(ht)+" | TTC : "+str(ttc)+" | TVA : "+str(tva))

print("done")
exit()
