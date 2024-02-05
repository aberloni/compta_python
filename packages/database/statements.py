"""
Sort all data extracted from bank listings
bank, date, amount, currency
"""


from datetime import datetime
from packages.database.database import DatabaseType
from modules.path import Path

class BankLogs:

    const_pending = "pending"

    def __init__(self, fileNameExt):

        

        #print("STATEMENT @"+fileNameExt)
        
        datas = fileNameExt.split("_")

        self.bank = datas[0]
        self.dtStart = datas[1]

        #lines = library.system.loadFile(fileName)
        lines = Path.getLinesFromStatement(fileNameExt)

        if lines == None:
            print("[error] no lines @ statements:"+fileNameExt)

        self.uid = fileNameExt

        #print("generating "+fileNameExt)

        self.statements = []
        for l in lines:

            if not l[0].isnumeric():
                continue
            
            st = Statement(self.bank, l)
            self.statements.append(st)

        #print("statement @"+fileNameExt+" x", len(self.statements))

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
    
class Statement:
    def __init__(self, bank, line):

        from packages.database.database import Database

        self.bank = bank
        self.line = line

        self.amount = 0
        self.currency = None

        if "sg" in self.bank:
            self.solveSG(line)
        elif "helios" in self.bank:
            self.solveHelios(line)
        else:
            print("(WARNING) bank not known : "+bank)

        self.creancier = Database.instance.creanciers.filterKeyContains(self.label)

    def solveHelios(self, line):

        datas = line.split(";")

        self.date = datetime.strptime(datas[0], "%d/%m/%Y")
        self.label = datas[2]
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

    def hasCreancier(self):
        return self.creancier is not None        

    def logUnknown(self):
        self.log()
        
        search = self.label.replace(" ","+")

        print("https://www.google.com/search?q="+search+" , https://www.google.com/maps/search/"+search)

    def log(self):
        output = str(self.date)
        
        output += "     €"+str(self.amount)

        if self.creancier is not None:
            output += "     @"+str(self.creancier.value)
        else:
            output += "     [unknown]"
        
        output += "     &"+self.label

        print(output)
