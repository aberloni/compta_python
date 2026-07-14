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

all_bills = []
for p in db.projects:
    all_bills.extend(p.getBills())

if len(all_bills) <= 0:
    print("no billing ?")

all_bills.sort(key=lambda b: b.uid)

from collections import defaultdict
by_year = defaultdict(list)
for b in all_bills:
    by_year[b.getDatetime().year].append(b)

for year in sorted(by_year.keys()):
    print(f"\n── {year} ──")
    for b in by_year[year]:
        ht = b.getHT()
        ttc = b.getTTC()
        tva = b.getTvaTotal()

        print(f"{b.getFullUid()} >> HT : {ht:g} | TTC : {ttc:g} | TVA : {tva:g}")

print("\ndone")
input("\nEntrée pour fermer...")
