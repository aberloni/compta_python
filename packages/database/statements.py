"""

    Statements are transactions lines registered by the bank
    actual money transfering that happened
    
Sort all data extracted from bank listings
bank, date, amount, currency
"""

import os

import modules.system
from modules.path import Path

class Statements:
    
    verbose = False
    
    logs = None # wrapper of each file within banks/
    statements = None # all lines within logs
    
    def __init__(self):
        
        Statements.instance = self
        
        self.fetchLogs()
        
        # for each line within banklogs
        # adds uniq statements (won't be ordered by date)
        self.statements = []
        for b in self.logs: # each banks files
            
            print("\n\n bank ? "+b.uid+" x"+str(len(b.statements)))
            
            print(" total is now x"+str(len(self.statements)))
                
            for s in b.statements:
                
                s.log()
                
                # filter duplicates
                if self.hasStatement(s):
                    print("--skip")
                else:
                    print("++stat")
                    self.statements.append(s)
        
        pass
    
        
    def fetchLogs(self):
        
        from packages.database.database import DatabaseType

        # path to statements/
        path = Path.getDbTypePath(DatabaseType.statements)
        #print(path)
        
        # wrapper for each bank file 
        # all files within all banks/
        self.logs = [] 

        # each bank folders within statements
        bankFolders = modules.system.getAllFilesInFolder(path)
        for b in bankFolders:
            
            b = b + "/"
            if self.verbose : print("bank : "+b)
            
            # each statements files for a given bank
            files = modules.system.getAllFilesInFolder(b)
            if len(files) <= 0:
                print(" ? no statements files in folder : "+b)
                continue
            
            if self.verbose: print("found x"+str(len(files))+" files")
            
            for filePath in files:
                
                # print(b+" >> "+c)
                tmp = BankLogs(filePath)
                self.logs.append(tmp)
        
        if self.verbose: print("total bank logs x"+str(len(self.logs)))
        pass
    
    # given statement is already added ?
    # duplicate ?
    def hasStatement(self, st):
        
        for stat in self.statements:
            if stat.compare(st): # same ?
                return True
            
        return False
    
    def extractClient(self, client):
        output = []
        
        #print("x"+str(len(self.statements)))
        
        for s in self.statements:
            if s.hasClient(client):
                output.append(s)
        
        if len(output) <= 0:
            print("/! no statements from client : "+client.creditor)
            
            for s in self.statements:
                print(s.creditor)
            
        return output
    
    def extractClientTimeframe(self, client, start, end):
        all = self.extractClient(client)
        
        output = []
        for s in all:
            if s.isTimeframe(start, end):
                output.append(s)
        
        return output

"""
wrapper containing all statements form a specific bank file
"""
class BankLogs:

    const_pending = "pending"

    statements = None # Statement[]

    def __init__(self, filePath):

        fileName = os.path.basename(filePath)
        self.uid = fileName

        lines = modules.system.loadFile(filePath)
        
        #print("STATEMENT @"+fileNameExt)
        #print(fileName)
        
        if lines == None:
            print("[error] no lines @ statements:"+fileName)
            return

        # extract bank from file path : parent folder name
        self.extractBank(filePath, fileName)

        # extract start date from file name
        self.extractStartDt(fileName)

        self.statements = []
        for line in lines:
            
            firstChar = line[0]

            # added lines, comments
            if firstChar == "#":
                continue
            
            # first character is NOT a number ?
            # all valid lines always (helios, sg) starts with a date
            if not firstChar.isnumeric():
                continue
            
            st = Statement(fileName, self.bank, line)
            self.statements.append(st)

        #print("statement @"+fileNameExt+" x", len(self.statements))

    def extractStartDt(self, fileName):
        
        if not self.bank:
            print("ERROR, need bank")
            return

        fileName = fileName[:-4] # remove ext

        match self.bank:
            case "sg":
                
                #00050179457_0303_0830

                datas = fileName.split("_")

                start = datas[len(datas)-2]
                #end = datas[len(datas)-1]

                date = start[4:] # yyyy
                date += "-"+start[2:4] # mm
                date += "-"+start[:2] # dd
                #print(start)
                #print(date)

                self.dtStart = date

            case "helios":
                
                # releve-mensuel-12-2023
                datas = fileName.split("-")

                if len(datas) < 2:
                    print("issue @ "+fileName+" ? DT")
                    return

                date = datas[3]         # year
                date += "-"+datas[2]    # month
                date += "-01"

                # yyyy-mm-dd
                self.dtStart = date
                
        
        #print("statement startdt : "+self.dtStart)


    def extractBank(self, filePath, fileName):

        self.bank = None

        # https://www.freecodecamp.org/news/how-to-substring-a-string-in-python/
        folder = filePath[:filePath.index(fileName) - 1]
        #print(folder)

        #idx = folder.rfind("\\")print(idx)
        folder = folder[folder.rfind("\\") + 1:]
        #print(folder)

        self.bank = folder

        #print("statement bank?"+self.bank)


    def isValid(self):
        return len(self.statements) > 0
    
    def countPositives(self, start, end):
        positives = self.getPositives(start, end)
        cnt = 0
        for p in positives:
            cnt += p.amount
        return cnt

    def getPositives(self, start, end):
        output = []
        for s in self.statements:

            if not s.isTimeframe(start, end):
                continue

            if s.amount > 0:
                output.append(s)

        return output





"""
A Statement is one line within a bank file
    label   : first
    labels  : all 3
"""
class Statement:

    bank = None         # concerned bank

    labels = None       # type of transaction (food, holiday, ...)
    creditor = None     # label of paid person
    currency = None     # EUR, USD, ...
    amount = 0          # 0000,00

    context = ""        # original file
    line = ""           # actual raw line
    
    def __init__(self, file, bank, line):

        from packages.database.creditor import Creditor

        self.context = file
        self.bank = bank
        self.line = line

        # solving labels
        match self.bank:
            case "sg":
                self.solveSG(line)
            case "helios":
                self.solveHelios(line)
        
        if self.labels is None:
            print("null labels ?")
            print(self.context+" : "+line)
        elif type(self.labels) is not list:
            print("labels is not a list ?")
            print(self.context+" : "+line)
        elif len(self.labels) <= 0:
            print("no labels solved ?")
            print(self.context+" : "+line)
        else:
            
            # solve what creditor is assoc to this transaction
            #self.creancier = Database.instance.creanciers.filterKeyContains(self.label)
            
            self.creditor = Creditor.instance.solveCreditorOfLabel(self.labels)
        
        #self.checkValidity()

    # param statement is the same as local one ?
    #
    def compare(self, statement):
        
        if self.amount != statement.amount: return False
        #if self.bank != statement.bank: return False
        
        return True

    def checkValidity(self):
        
        res = True
        output = "issues:"

        if self.bank is None :
            output += "\n   bank not known : "+self.bank
            res = False
        if self.creditor is None:
            output += "\n   no creditor"
            res = False
        
        if not res:
            print("\n(WARNING) invalid statement")
            print(self.line)
            print(output)

        return res
    
    def hasIssues(self):
        if self.creditor is None :
            return True
        
        return False

    def solveHelios(self, line):

        from datetime import datetime

        datas = line.split(";")

        # date; null; label; payment type; category; ...; amount
        self.line = line
        
        # date
        self.date = datetime.strptime(datas[0], "%d/%m/%Y")
        
        # default label
        self.label = datas[2]

        # labels
        # funnel all field before amount
        lastLabelIndex = len(datas)-2
        self.labels = []
        if len(datas) > 4:
            for i in range(1, lastLabelIndex):
                self.labels.append(datas[i])
        else:
            self.labels.append(self.label)
        
        # last is amount
        self.amount = float(datas[len(datas)-1])
        self.amount = round(self.amount, 2)
        self.currency = "EUR"

    def solveSG(self, line):

        from datetime import datetime

        #print(line)

        # FORMAT
        #   DD/MM/YYYY;SHORT LABEL;AMOUNT;CURRENCY;
        #   DD/MM/YYYY;SHORT LABEL;LONG LABEL;AMOUNT;CURRENCY;
        
        # ! last index is empty, all lines ends with ;
        # remove it
        if line[-1] == ";": line = line[0:-1]
        
        datas = line.split(";")
        if len(datas) <= 0:
            print("(SG) no data ?")
            print(line)
            return
        
        #print(datas)print(line)

        # #0 = date
        self.date = datetime.strptime(datas[0], "%d/%m/%Y")
        
        # #1 = base label
        self.label = datas[1]
        
        # funnel all fields before amount
        self.labels = []
        if len(datas) > 4: # has enough data ?
            
            # last 2 slots are AMOUNT & CURRENCY
            for i in range(1,len(datas)-2):
                self.labels.append(datas[i])
                
        else:
            self.labels.append(self.label)
        
        # penultimate is amount
        _amount = datas[len(datas)-2]
        if "," in _amount: _amount = _amount.replace(",",".") # compat
        _amount = float(_amount)        # to numeric
        self.amount = round(_amount, 2) # round

        # currency is last
        self.currency = datas[len(datas)-1] # EUR

    def getMonth(self):
        return self.date.strftime("%m")

    """
    str YYYY-mm-dd will be converted to datetime.date
    """
    def isTimeframe(self, start, end):
        
        import datetime
        #from datetime import datetime

        dtStart = start
        #print(type(start))

        if not isinstance(start, datetime.datetime):
            dtStart = datetime.strptime(start, "%Y-%m-%d")
        
        dtEnd = end
        if not isinstance(end, datetime.datetime):
            dtEnd = datetime.strptime(end, "%Y-%m-%d")

        return self.date >= dtStart and self.date <= dtEnd

    def hasCreditor(self):
        return self.creditor is not None

    def hasClient(self, client):
        
        # search in labels (all fields of the log)
        for lbl in self.labels:
            if client.creditor in lbl:
                return True
        
        # fallback, is it creditor ?
        return self.creditor == client.creditor

    def logUnknown(self):
        print("\nUNKNOWN : "+self.label)
        
        # local variables details
        self.log()

        # original line
        print("raw : "+self.line)
        
        # helpers
        search = self.label.replace(" ","+")
        print("google ? https://www.google.com/search?q="+search)
        print("maps   ? https://www.google.com/maps/search/"+search)

    def log(self):
        
        output = str(self.date)
        
        output += " >> "+self.bank+ " & "+self.context+" >>   "
        output += "     €"+str(self.amount)

        if self.hasCreditor():
            output += "     creditor:"+str(self.creditor)
        else:
            output += "     creditor:[unknown]"
        
        output += " label"+self.label

        for l in self.labels:
            output += "\n    > "+l

        print(output)
