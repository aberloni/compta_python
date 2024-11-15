import os
import configs

from packages.export.htmlFormater import *
from modules.path import Path
    
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

def exportBills(project, yearsToExport):

    """
    if yearsToExport != None:
        print("FILTER YEARS x "+str(len(yearsToExport)))
        for y in yearsToExport: 
            print(y)
    """
    
    bills = project.getBills(yearsToExport)

    cnt = len(bills)
    print("project has x"+str(cnt)+" bills");

    if len(bills) <= 0:
        
        print(" /! no bills for "+project.uid)

    else:
        
        for b in bills:
            exportBill(project, b)
    

def exportBill(project, bill):

    _billFuid = bill.getBillFullUid()

    if _billFuid == None:
        print("could not solve fullUID of bill # "+bill.uid)
        return

    print("     export.bill uid:"+bill.uid+" , fuid:"+_billFuid)

    # folder export path
    exportPath = Path.getExportBillingPath()
    #print("     bill.path @ "+exportPath)

    # export file name
    billFileName = _billFuid+"_"+project.client.uid+"_"+project.uid

    # GENERATE DUMP FILE
    pathDump = exportPath+billFileName+".dump"
    f = open(pathDump, "w")
    f.write(bill.dump())
    f.close()
    
    #print("saved dump @ "+pathDump)

    if configs.openBillingDumpFile:
        print("opening dump @ "+pathDump)

        # https://stackoverflow.com/questions/43204473/os-startfile-path-in-python-with-numbers
        os.startfile(pathDump)

    # GENERATE HTML

    generateHtml(project, bill, billFileName)

    # [drive]:\[path_to_cloned_folder\
    # print(localPath)

    if configs.openBillingHtmlFile:
        path = "file:///"+exportPath+billFileName+".html"

        print("opening html @ "+path)

        import webbrowser
        #webbrowser.open(htmlFile,new=2)
        webbrowser.open_new_tab(path)
