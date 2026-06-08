import os
import configs

from packages.export.htmlFormater import *
from modules.path import Path

from weasyprint import HTML

def clearExportFolder():
    path = getLocalPath()
    path += configs.pathExport

    # ...

# get basepath to code folder/
# 
def getLocalPath():
    
    localPath = os.getcwd()
    localPath = localPath.replace("\\","/").strip()
    localPath += "/"

    return localPath

def exportBills(project, exportDateRange):

    bills = project.getBills(exportDateRange)
    print("x"+str(len(bills)))
          
    if len(bills) > 0:
        for b in bills:
            exportBill(project, b)

    return bills


# export to .dump & .html
#
def exportBill(project, bill):

    _billFuid = bill.getFullUid()

    if _billFuid == None:
        print("could not solve fullUID of bill # "+bill.uid)
        return

    print("     export.bill uid:"+bill.uid+" , fuid:"+_billFuid)

    # folder export path
    exportPath = Path.getExportBillingPath()
    #print("     bill.path @ "+exportPath)

    # export file name
    billFileName = _billFuid+"_"+project.client.uid+"_"+project.uid

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

def openBillInFolder(billFileName):
    exportPath = Path.getExportBillingPath()
    path = "file:///"+exportPath+billFileName+".html"

    print("opening html @ "+path)
    
    import webbrowser
    #webbrowser.open(htmlFile,new=2)
    webbrowser.open_new_tab(path)

def openDumpFile(pathDump):
    
    print("opening dump @ "+pathDump)

    # https://stackoverflow.com/questions/43204473/os-startfile-path-in-python-with-numbers
    os.startfile(pathDump)
