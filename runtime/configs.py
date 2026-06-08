import sys
import os

# database files extension
dbExtension = ".compta"
statementsExtension = ".csv"

# BILLING
pathBilling = "billings/"

# all years to export
billingRange = ["2026-01","2026-03"]

# create pdf
creatPdf = True

# open after process
openBillingFolder = True

# TEST MODE
# set testMode = False to use real data via externals.lnk
testMode = True
testDbPath = os.path.abspath(os.path.join(os.path.dirname(__file__), "../__testdb")) + "/"

def is_debugging():
    return sys.gettrace() is not None
