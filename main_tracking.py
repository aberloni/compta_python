"""
    display tracking info
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

print("=== TRACKING")

for sf in db.statements:
    print("statement uid : "+sf.uid)
    print("statements quantity x", len(sf.statements))

    for s in sf.statements:
        if not s.hasCreancier():
            s.logUnknown()


# export/dump result

#path = Path.getExportStatementsFolder()
#os.startfile(path)

exit()