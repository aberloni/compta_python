
from datetime import datetime
import calendar

"""
https://stackoverflow.com/questions/4130922/how-to-increment-datetime-by-custom-months-in-python-without-using-library
"""
def add_months(sourcedate, months):

    month = sourcedate.month - 1 + months
    year = sourcedate.year + month // 12
    month = month % 12 + 1
    day = min(sourcedate.day, calendar.monthrange(year,month)[1])
    #return datetime.date(year, month, day)
    return sourcedate.replace(year, month, day)



"""
generic viewer
"""
class Viewer:

    
    months = []
    
    def __init__(self):
        self.months = []
    
    """
    str YYYY-mm-dd
    """
    def solve(self, strStart, monthCount):
        
        tmp = datetime.strptime(strStart, "%Y-%m-%d")
        print("view start @ "+strStart)
        
        dtEnd = tmp
        for i in range(0, monthCount):
            
            dtEnd = add_months(tmp, 1)
            
            # month -> next month
            vMonth = ViewRange(tmp, dtEnd)
            self.months.append(vMonth)
            
            tmp = add_months(tmp, 1)
            
        #print("solved x"+str(len(self.months)))
        
        #for m in self.months: print(str(m.date)+" x"+str(len(m.statements)))
    
    def log(self, statementAmount = None):
        print("===RESULT===")

        positif = 0
        negatif = 0
        total = 0
        
        for month in self.months:
            month.log(statementAmount)

            positif += month.positif
            negatif += month.negatif
            total += month.total
        
        print("===TOTAL===")
        print("positif  : "+str(positif))
        print("negatif  : "+str(negatif))
        print("total    : "+str(total))
            





"""
a view that counts based on date range
"""
class ViewRange:

    positif = 0
    negatif = 0
    total = 0

    countIssues = 0

    statements = None

    def __init__(self, dStart, dEnd):
        
        from packages.database.statements import Statements
        
        self.date = dStart
        
        # get ALL stats
        _stats = Statements.instance.statements
        
        self.statements = []
        
        # find matching timeframe stats
        for s in _stats:
            
            if s.isTimeframe(dStart, dEnd):
                
                self.statements.append(s)
                s.log()
                
                val = s.amount
                if val > 0: self.positif += val
                elif val < 0: self.negatif += val
                self.total += val
                
                if s.hasIssues():
                    self.countIssues += 1
        
        #print("\n+month "+str(self.date)+" -> "+str(dEnd))
        #print("     x"+str(len(self.statements)))
        
        #for s in self.statements: s.log()
        
        
    def log(self, statementAmount = None):
        print("\n"+str(self.date.year)+"-"+str(self.date.month))
        print("  credit : "+str(self.positif))
        print("   debit : "+str(self.negatif))
        print("resultat : "+str(self.total)+" €")

        if statementAmount is not None:
            for s in self.statements:
                if abs(s.amount) > abs(statementAmount):
                    s.log()

    def logDuplicates(self, dispAmount):
    
        print("log : "+str(self.date)+" x "+str(len(self.statements)))
        
        for i in range(0, len(self.statements)):
            
            for j in range(i+1, len(self.statements)):
                
                a = self.statements[i]
                b = self.statements[j]
                
                if a.compare(b):
                    print(str(self.date)+"  DUPLICATE! #"+str(i)+" VS #"+str(j))
                    a.log()
                    b.log()
                    dispAmount -= 1
                    if dispAmount <= 0:
                        return

