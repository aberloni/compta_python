
from datetime import datetime
from library.database import DatabaseType

class Statements:

    def __init__(self, fileNameExt):

        from library.path import Path

        #print("STATEMENT @"+fileNameExt)

        #lines = library.system.loadFile(fileName)
        lines = Path.getLinesFromStatement(fileNameExt)

        if lines == None:
            print("[error] no lines @ statements:"+fileNameExt)

        self.statements = []
        for l in lines:

            if not l[0].isnumeric():
                continue
            
            st = Statement(l)
            self.statements.append(st)
            st.log()

        print("statement @"+fileNameExt+" x", len(self.statements))

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
    def __init__(self, line):

        self.line = line

        datas = line.split(";")

        self.date = datetime.strptime(datas[0], "%d/%m/%Y")

        self.short = datas[1]
        self.label = datas[2]

        amount = datas[3]
        amount = amount.replace(",",".")
        self.amount = round(float(amount), 2)
        self.devise = datas[4] # EUR

    def isTimeframe(self, start, end):
        dtStart = datetime.strptime(start, "%Y-%m-%d")
        dtEnd = datetime.strptime(end, "%Y-%m-%d")

        return self.date >= dtStart and self.date <= dtEnd
        

    def log(self):
        print(str(self.date)+"      "+str(self.amount)+self.devise+"       @"+self.label)