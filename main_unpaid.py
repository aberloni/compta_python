"""
    WIP
    show unpaid bills & amounts
"""

import locale
locale.setlocale(locale.LC_ALL, 'fr_FR')

# DATABASE LOADER

import os

from library.database import Database
from library.path import Path

# load all data
db = Database.tracking()

# do something with it
#print(db)

"""
for s in db.statements:
    #print(s.countPositives("2023-01-01", "2023-12-31"))
    print(s.countPositives("2023-09-01", "2023-09-30"))
"""

unpaids = db.solveUnpaid()

for bill in unpaids:
    print("billd?"+bill.uid+ " ttc?"+bill.getTTC())

# export/dump result

path = Path.getExportStatementsFolder()
print("tracking : open folder @ "+path)
os.startfile(path)

exit()