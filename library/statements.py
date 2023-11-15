
from datetime import datetime
from library.database import DatabaseType

class BankLogs:

    def __init__(self, fileNameExt):

        from library.path import Path

        #print("STATEMENT @"+fileNameExt)

        datas = fileNameExt.split("_")
        self.bank = datas[0]
        self.dtStart = datas[1]

        #lines = library.system.loadFile(fileName)
        lines = Path.getLinesFromStatement(fileNameExt)

        if lines == None:
            print("[error] no lines @ statements:"+fileNameExt)

        self.uid = fileNameExt

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

        from library.database import Database

        self.bank = bank
        self.line = line
        
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
        self.devise = "EUR"

    def solveSG(self, line):

        datas = line.split(";")

        self.date = datetime.strptime(datas[0], "%d/%m/%Y")
        
        #self.short = datas[1]
        self.label = datas[2]

        amount = datas[3]

        if "," in amount:
            amount = amount.replace(",",".")
        
        self.amount = round(float(amount), 2)

        if len(datas) > 4:
            self.devise = datas[4] # EUR

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
            output += "     "+str(self.creancier.value)
        else:
            output += "     [unknown]"
        
        output += "     &"+self.label

        print(output)
