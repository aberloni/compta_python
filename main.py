
import locale
locale.setlocale(locale.LC_ALL, 'fr_FR')

# DATABASE LOADER

import os
import configs

from library.database import Database

database = Database()

print("done importing")

import library.exporter

projects = ["tinies", "unfortune", "makina", "spaces"]

for p in projects:
    
    curProject = database.getProject(p)
    
    if curProject == None:
        print("couldn't not solve project # "+p)
    else:
        print(" === EXPORT === > "+curProject.uid)
        library.exporter.exportBills(curProject)

if configs.openDumpFolder:
    path = library.exporter.getLocalPath()
    path = path + configs.pathExport

    print("open folder @ "+path)
    os.startfile(path)

print("done")
exit()