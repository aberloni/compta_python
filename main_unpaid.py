"""
    DEPRECATED
    NOT WORKNIG
"""

# show unpaid bills & amounts

import locale
locale.setlocale(locale.LC_ALL, 'fr_FR')

# DATABASE LOADER

import os

# load all data
# db = Database.tracking()

unpaids = db.solveUnpaid()

for bill in unpaids:
    print("billd?"+bill.uid+ " ttc?"+bill.getTTC())

# export/dump result

path = Path.getExportStatementsFolder()
print("tracking : open folder @ "+path)
os.startfile(path)

exit()