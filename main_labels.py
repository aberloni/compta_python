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
db = Database.init_labels()

dtStart = "2024-01-01"
dtEnd = "2024-08-31"

print("from : "+dtStart+"       to : "+dtEnd)

view = Viewer()
view.solve(db, dtStart, dtEnd)
view.log(100)

exit()