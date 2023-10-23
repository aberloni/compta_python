import os

import configs

def clearExportFolder():
    path = getLocalPath()
    path += configs.pathExport

    # ...

def getLocalPath():
    
    localPath = os.getcwd()
    localPath = localPath.replace("\\","/").strip()
    localPath += "/"

    return localPath

def exportBills(project):



    bills = project.getBills()

    if len(bills) <= 0:
        
        print("no bills for "+project.uid)

    else:
        for b in bills:
            exportBill(project, b)
    

def exportBill(project, bill):

    import library.htmlFormater

    print(" === NOW EXPORTING BILL : "+bill.uid)

    billFuid = bill.getBillFullUid()

    if billFuid == None:
        print("none fuid : "+bill.uid)
        return

    localPath = getLocalPath()

    billFileName = billFuid+"_"+project.client.uid+"_"+project.uid

    print(" === TARGET FILE === > "+billFileName)
    # DUMP

    path = configs.pathExport+billFileName+".dump"
    f = open(path, "w")
    f.write(bill.dump())
    f.close()

    # abs path
    path = localPath + path

    if configs.openDumpFile:
        print("opening dump @ "+path)

        # https://stackoverflow.com/questions/43204473/os-startfile-path-in-python-with-numbers
        os.startfile(path)

    # GENERATE HTML

    library.htmlFormater.generateHtml(project, bill, billFileName)

    # [drive]:\[path_to_cloned_folder\
    # print(localPath)

    if configs.openHtmlFile:
        path = "file:///"+localPath+configs.pathExport+billFileName+".html"

        print("opening html @ "+path)

        import webbrowser
        #webbrowser.open(htmlFile,new=2)
        webbrowser.open_new_tab(path)

    print("exported : "+billFileName)
