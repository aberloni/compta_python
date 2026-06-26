import sys
import os

# database files extension (legacy fallback)
dbExtension = ".compta"

DB_EXTENSIONS = {
    "clients":   ".cli",
    "tasks":     ".task",
    "projects":  ".proj",
    "bills":     ".bill",
    "infos":     ".info",
    "creditors": ".cred",
    "statements":".csv",
    "wiring":    ".wire",
}
statementsExtension = ".csv"

# BILLING
pathBilling = "billings/"

# all years to export
billingRange = ["2026-01","2026-07"]

# create pdf
creatPdf = True

# open after process
openBillingFolder = True

# keep terminal open after view scripts (set False when running from an IDE terminal that stays open)
pause_on_exit = False

# TEST MODE
# set testMode = False to use real data via externals.lnk
testMode = True
testDbPath = os.path.abspath(os.path.join(os.path.dirname(__file__), "../externals")) + "/"

def is_debugging():
    return sys.gettrace() is not None
