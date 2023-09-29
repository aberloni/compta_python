
import locale
locale.setlocale(locale.LC_ALL, 'fr_FR')

# DATABASE LOADER

import generate
database = generate.Database()

project = database.getProject("Tinies")

"""
if project == None:
    print("can't dump")
else:
    project.dump()
"""

print("done importing")

import htmlFormater
import configs

htmlFormater.generateHtml(configs.htmlExportDefault, project, "2023-09")

print("done")