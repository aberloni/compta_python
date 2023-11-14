
import locale
locale.setlocale(locale.LC_ALL, 'fr_FR')

# DATABASE LOADER

import os
import configs

from library.database import Database

db = Database()

print("done importing")

import library.exporter
import library.system

"""
lnkPath = library.system.getSubdirPath("projects")

print(lnkPath)

pFiles = library.system.getAllFilesFromLnk(lnkPath)

print(len(pFiles)+" projects to export")

projects = []
for p in pFiles:
    pName = p.split("_")[1]
    pName = pName.split(".")[0]
    projects.append(pName)

# projects = ["tinies", "unfortune", "makina", "spaces", "kasbah"]
"""

for p in db.projects:
    #curProject = db.getProject(p)
    
    print(" === EXPORT === > "+p.uid)
    library.exporter.exportBills(p)

if configs.openDumpFolder:
    path = library.exporter.getLocalPath()
    path = path + configs.pathExport

    print("open folder @ "+path)
    os.startfile(path)

print("done")
exit()