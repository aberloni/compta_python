
from packages.database import database
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

class ViewRange:

    positif = 0
    negatif = 0
    total = 0

    countIssues = 0

    statements = None

    """
    s = date start
    e = date end
    """
    def __init__(self, db, dStart, dEnd):
        
        self.date = dStart
        #print("@"+self.month)

        self.statements = []
        for s in db.statements:
            timeRange = s.isTimeframe(dStart, dEnd)

            if timeRange:
                
                self.statements.append(s)

                val = s.amount
                if val > 0: self.positif += val
                elif val < 0: self.negatif += val
                self.total += val
                
                if s.hasIssues():
                    self.countIssues += 1



    def log(self, statementAmount = None):
        print("\n"+str(self.date.year)+"-"+str(self.date.month))
        print("  credit : "+str(self.positif))
        print("   debit : "+str(self.negatif))
        print("resultat : "+str(self.total)+" €")

        if statementAmount is not None:
            for s in self.statements:
                if abs(s.amount) > abs(statementAmount):
                    s.log()

        

class Viewer:

    
    months = []
    
    def __init__(self):
        self.months = []
    
    """
    str YYYY-mm-dd
    """
    def solve(self, db, dtStart, dtEnd):
        
        dEnd = datetime.strptime(dtEnd, "%Y-%m-%d")
        tmp = datetime.strptime(dtStart, "%Y-%m-%d")
        print("view start @ "+dtStart)

        # each months
        while tmp < dEnd:
            nextMonth = add_months(tmp, 1)
            #print("   next : "+str(nextMonth))

            vMonth = ViewRange(db, tmp, nextMonth)
            self.months.append(vMonth)

            tmp = nextMonth
        
        print("done")

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
            


