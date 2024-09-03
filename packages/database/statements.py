"""
Sort all data extracted from bank listings
bank, date, amount, currency
"""

from datetime import datetime
from packages.database.database import DatabaseType
import modules.system
import os

"""
all statements form a specific bank file
"""
class BankLogs:

    const_pending = "pending"

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
        self.extractStartDt(fileName)

        self.statements = []
        for l in lines:

            if not l[0].isnumeric():
                continue
            
            st = Statement(fileName, self.bank, l)
            self.statements.append(st)

        #print("statement @"+fileNameExt+" x", len(self.statements))

    def extractStartDt(self, fileName):
        
        fileName = fileName[:-4] # remove ext

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
one line within a bank file
"""
class Statement:
    def __init__(self, contextFile, bank, line):

        from packages.database.database import Database

        self.context = contextFile
        
        self.bank = bank
        self.line = line

        self.amount = 0
        self.currency = None

        # solving labels
        if "sg" in self.bank:
            self.solveSG(line)
        elif "helios" in self.bank:
            self.solveHelios(line)
        else:
            print("(WARNING) bank not known : "+bank)

        # solve what creditor is assoc to this transaction
        #self.creancier = Database.instance.creanciers.filterKeyContains(self.label)
        
        self.creditor = Database.instance.creditors.solveCreditorOfLabel(self.labels)
        
        if not self.hasCreditor():
            print("\nUNKNOWN : "+self.label)
            self.logUnknown()
            
            exit("(STOP) first unknown")
        
    def solveHelios(self, line):

        datas = line.split(";")

        # date; null; Steam Purchase; payment type; category; category; amount
        self.line = line
        
        self.date = datetime.strptime(datas[0], "%d/%m/%Y")
        
        self.label = datas[2]
        self.labels = datas[2]+" "+datas[3]+" "+datas[4]
        
        self.amount = round(float(datas[6]), 2)
        self.currency = "EUR"

    def solveSG(self, line):

        #print(line)

        # FORMAT
        #   DD/MM/YYYY;SHORT LABEL;LONG LABEL;AMOUNT;CURRENCY
        
        datas = line.split(";")

        #print(datas)print(line)

        self.date = datetime.strptime(datas[0], "%d/%m/%Y")
        
        self.label = datas[1]

        _amount = datas[2]
        
        #print(line)print(_amount)

        if "," in _amount:
            _amount = _amount.replace(",",".")
        
        self.amount = round(float(_amount), 2)

        if len(datas) > 3:
            self.currency = datas[3] # EUR

        #print(self.label)
        
    

    def isTimeframe(self, start, end):
        dtStart = datetime.strptime(start, "%Y-%m-%d")
        dtEnd = datetime.strptime(end, "%Y-%m-%d")

        return self.date >= dtStart and self.date <= dtEnd

    def hasCreditor(self):
        return self.creditor is not None        

    def logUnknown(self):
        self.log()
        
        print("raw : "+self.line)
        
        search = self.label.replace(" ","+")

        print("google ? https://www.google.com/search?q="+search)
        print("maps   ? https://www.google.com/maps/search/"+search)

    def log(self):
        
        output = str(self.date)
        
        output += " >> "+self.bank+ " & "+self.context+" >>   "
        output += "     €"+str(self.amount)

        if self.hasCreditor():
            output += "     creditor:"+str(self.creditor.value)
        else:
            output += "     [unknown]"
        
        output += "     label:"+self.label

        print(output)
