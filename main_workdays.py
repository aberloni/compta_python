"""
    (UN)WORKED DAYS
    OFF DAYS
"""

import locale
locale.setlocale(locale.LC_ALL, 'fr_FR')

# DATABASE LOADER

from packages.database.database import Database
from datetime import datetime
from packages.views.TasksMonth import TasksMonth

instance = Database()

years = [2023,2024]

tasks = instance.fetch_tasks()

yTasks = {}

for y in years:
    
    months = yTasks.setdefault(y, [])

    for i in range(1,12):
        t = TasksMonth(y, i, tasks)
        months.append(t)
    
    yTasks[y] = months

for y in yTasks:

    print("y:"+str(y))

    months = yTasks[y]

    miss = 0
    work = 0
    for m in months:
        miss += m.countMissingDays()
        work += m.countWorkDays()
        print(m.stringify())
    
    miss = abs(miss)
    
    print("missing days :   "+str(miss)+" / "+str(work))

    perc = miss / work
    perc *= 100

    print(str(perc)+"% non-worked days")

exit()
