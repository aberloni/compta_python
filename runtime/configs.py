import sys
import os

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

# all years to export
billingRange = ["2026-01","2026-07"]

# create pdf
creatPdf = True

# open after process
openBillingFolder = True

# keep terminal open after view scripts (set False when running from an IDE terminal that stays open)
pause_on_exit = False

# path to database/ folder at repo root
dbPath = os.path.abspath(os.path.join(os.path.dirname(__file__), "../")) + "/"

def is_debugging():
    return sys.gettrace() is not None
