
import locale
locale.setlocale(locale.LC_ALL, 'fr_FR')

# DATABASE LOADER

import generate
database = generate.Database()

print("done importing")

project = database.getProject("Tinies")

if project == None:
    print("no project ?")
    exit()
    pass

# EXPORT

import exporter;

exporter.exportBills(project)