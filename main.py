
import locale
locale.setlocale(locale.LC_ALL, 'fr_FR')

# DATABASE LOADER

import configs
from database import Database

database = Database()

print("done importing")

import exporter;

projects = ["tinies", "unfortune"]

for p in projects:
    
    curProject = database.getProject(p)
    
    if curProject == None:
        print("couldn't not solve project # "+p)
    else:

        print(" === EXPORT === > "+curProject.uid)

        exporter.exportBills(curProject)



import configs

if configs.openDumpFolder:
    import os
    path = exporter.getLocalPath()
    path = path + configs.pathExport

    print("open folder @ "+path)
    os.startfile(path)

print("done")
exit()