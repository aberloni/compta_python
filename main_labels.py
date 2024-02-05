"""
    WIP
    display some data based on statements from bank
"""

import locale
locale.setlocale(locale.LC_ALL, 'fr_FR')

# DATABASE LOADER

import os

from packages.database.database import Database

# load all data
db = Database.tracking()

# do something with it
#print(db)

exit()


print("\n\n")
print(" ... logging unknown statements labels")

for sf in db.statements:

    print(f"{sf.uid} x{len(sf.statements)}")

    for s in sf.statements:
        if not s.hasCreancier():
            s.logUnknown()


# export/dump result

#path = Path.getExportStatementsFolder()
#os.startfile(path)

exit()
