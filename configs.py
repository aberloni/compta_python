import sys

#import library.exporter

# database files extension
dbExtension = ".compta"
statementsExtension = ".csv"

# BILLING

pathBilling = "billings/"

# all years to export
billingRange = ["2026-01","2026-03"]
#pdfExportRange = ["2025-09","2025-10"]

# create
creatPdf = True

# open after process
openBillingFolder = True

def is_debugging():
    return sys.gettrace() is not None
