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
db = Database.init_labels()

# do something with it
#print(db)
exit()

print("\n\n")
print(" ... logging unknown statements labels")

cnt = 10

for sf in db.statements: # each banklogs

    print(f"{sf.uid} x{len(sf.statements)}")

    for s in sf.statements: # each line
        
        if not s.hasCreditor():
            s.logUnknown()
            cnt = cnt-1
        
        if cnt < 0:
            exit("limit")
        


# export/dump result

#path = Path.getExportStatementsFolder()
#os.startfile(path)

exit()
