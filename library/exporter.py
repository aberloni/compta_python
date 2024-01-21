import os
import configs

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

def exportBills(project):

    bills = project.getBills()

    if len(bills) <= 0:
        
        print(" /! no bills for "+project.uid)

    else:
        
        for b in bills:
            exportBill(project, b)
    

def exportBill(project, bill):

    import library.htmlFormater
    import library.system
    from library.path import Path

    billFuid = bill.getBillFullUid()

    print("\n\n === NOW EXPORTING BILL "+bill.uid+" # "+billFuid)

    if billFuid == None:
        print("none fuid : "+bill.uid)
        return

    exportPath = Path.getExportBillingPath()
    print("export path @ "+exportPath)

    #localPath = getLocalPath()

    billFileName = billFuid+"_"+project.client.uid+"_"+project.uid

    #print(" === TARGET FILE === > "+billFileName)
    # DUMP

    pathDump = exportPath+billFileName+".dump"
    f = open(pathDump, "w")
    f.write(bill.dump())
    f.close()
    
    print("saved dump @ "+pathDump)

    if configs.openBillingDumpFile:
        print("opening dump @ "+pathDump)

        # https://stackoverflow.com/questions/43204473/os-startfile-path-in-python-with-numbers
        os.startfile(pathDump)

    # GENERATE HTML

    library.htmlFormater.generateHtml(project, bill, billFileName)

    # [drive]:\[path_to_cloned_folder\
    # print(localPath)

    if configs.openBillingHtmlFile:
        path = "file:///"+exportPath+billFileName+".html"

        print("opening html @ "+path)

        import webbrowser
        #webbrowser.open(htmlFile,new=2)
        webbrowser.open_new_tab(path)
