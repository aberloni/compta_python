import locale

locale.setlocale(locale.LC_ALL, 'fr_FR')

import os

from packages.database.database import Database
from datetime import datetime
from packages.database.statements import Statements

db = Database.init_all()

#print("projects     x"+str(len(db.projects)))
#print("clients     x"+str(len(db.clients)))

strStart = "2024-01-01"
strEnd = "2024-12-31"

print("from : "+strStart+"       to : "+strEnd)

dtStart = datetime.strptime(strStart, "%Y-%m-%d")
dtEnd = datetime.strptime(strEnd, "%Y-%m-%d")

# fetch all timeframe bills

darj = Database.instance.getClient("darjeeling")
print(darj.name)

st =  Statements.instance.extractClientTimeframe(darj, dtStart, dtEnd)
print("x"+str(len(st)))

amount = 0

for s in st:
    s.log()
    amount += s.amount

print("amount ? "+str(amount))

exit()

bills = []
for p in db.projects:
    
    for b in p.bills:
        if b.isTimeframe(dtStart, dtEnd):
            bills.append(b)
            
    pass

print("bills x "+str(len(bills)))

#for b in bills: print(b.getFullUid())

unpaids = []
for b in bills:
    
    pass