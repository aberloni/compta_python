"""
    WIP
    display some data based on statements from bank
"""

import os

from datetime import datetime

import locale
locale.setlocale(locale.LC_ALL, 'fr_FR')

# DATABASE LOADER

from packages.database.database import Database
from modules.viewer import Viewer

# load all data
Database.init_labels()

strStart = "2025-01-01"
monthCount = 2

print("from : "+strStart+"  +"+str(monthCount)+" months")

view = Viewer()
view.solve(strStart, monthCount)

#view.log(100)

#for m in view.months: m.logDuplicates(2)

exit()