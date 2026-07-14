import os
import configs

from packages.export.htmlFormater import *
from modules.path import Path

from weasyprint import HTML

def exportBills(project, exportDateRange):
    """Export all bills of a project within the given date range. Returns the bill list."""
    bills = project.getBills(exportDateRange)
    print("x"+str(len(bills)))
          
    if len(bills) > 0:
        for b in bills:
            exportBill(project, b)

    return bills


def exportBill(project, bill):
    """Generate HTML (and PDF if creatPdf) for a single bill. Writes to exports/billings/."""
    _billFuid = bill.getFullUid()

    if _billFuid == None:
        print("could not solve fullUID of bill # "+bill.uid)
        return

    print("     export.bill uid:"+bill.uid+" , fuid:"+_billFuid)

    # folder export path
    exportPath = Path.getExportBillingPath()
    #print("     bill.path @ "+exportPath)

    # export file name
    billFileName = _billFuid+"_"+bill.getClient().uid+"_"+project.uid

    if configs.is_debugging():
        # GENERATE DUMP FILE
        pathDump = exportPath+billFileName+".dump"
        f = open(pathDump, "w")
        f.write(bill.dump())
        f.close()
    
    #print("saved dump @ "+pathDump)

    # GENERATE HTML

    htmlPath = generateHtml(project, bill, billFileName)

    # [drive]:\[path_to_cloned_folder\
    # print(localPath)

    # generate PDF
    if configs.creatPdf:
        HTML(htmlPath).write_pdf(exportPath+billFileName+".pdf")
        os.remove(htmlPath)

