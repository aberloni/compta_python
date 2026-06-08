from datetime import datetime
from datetime import timedelta
import calendar

from modules.system import *


def _iter_months(start, end):
    """Yield (year, month) tuples from start to end datetimes inclusive."""
    cy, cm = start.year, start.month
    ey, em = end.year, end.month
    while (cy, cm) <= (ey, em):
        yield (cy, cm)
        cm += 1
        if cm > 12:
            cm = 1
            cy += 1

"""
date de facturation:{start},{end}|montant fixe
{math sign}label, prix, quantité
"""

class Bill:
    
    verbose = False
    
    uid = None # YYYY-MM-DD
    project = None # {project}
    
    # {YYYY-MM}_s{week year}-{incrmental}
    # use getter to generate
    fullUID = None
    
    # public fields filled by parent project
    label = "" # label of prestation (with days count)
    designation = "" # label of billing (above days array)
    
    start = None # date.start
    end = None   # date.end
    
    tasks = None # [] all tasks line of this project
    
    limit = None # payment limit date
    
    def __init__(self, project, uid, billHeader):
        
        self.project = project
        self.uid = uid # 2023-09-XX

        self.log("      bill.header : "+billHeader)
        
        # https://stackoverflow.com/questions/6871016/adding-days-to-a-date-in-python

        # get payment limit date
        self.limit = datetime.strptime(self.uid, "%Y-%m-%d")
        self.limit = self.limit + timedelta(days=30)
        self.limit = self.limit.strftime("%Y-%m-%d")
        
        # forfait is | after dates
        self.forfait = None
        self.transactions = []

        self.injectData(billHeader)

    def addTransaction(self, key, value):
        bt = BillTransaction(key, value)
        self.transactions.append(bt)
        
        if self.verbose: print("+Frais :  bill:"+self.uid+" --> x"+str(len(self.transactions)))

    # during constructor
    #
    def injectData(self, data):

        # | is to override day count
        if "|" in data:
            splitted = data.split("|")
            data = splitted[0]
            self.forfait = float(splitted[1])

        _dtSplit = data.split(",")

        # real datetime, not strings
        
        self.log("    bill.range : "+_dtSplit[0]+" -> "+_dtSplit[1])

        self.start = datetime.strptime(_dtSplit[0], "%Y-%m-%d")

        # date must be valid
        try:
            self.end = datetime.strptime(_dtSplit[1], "%Y-%m-%d")
        except ValueError:
            print("ERROR : invalid date : ",_dtSplit[1])
            
        # gather all tasks related to this bill
        self.tasks = []
        for t in self.project.tasks:
            if t.isDateRange(self.start, self.end):
                self.tasks.append(t)

        self.log("    bill.tasks x "+str(len(self.tasks))+" / total in project x "+str(len(self.project.tasks)))

    def getClient(self):
        """Return the client applicable at the start of this bill's period."""
        return self.project.getClient(self.start)

    def hasTransactions(self):
        return len(self.transactions) > 0
            

    # same bill uid && same project uid
    #
    def compareBill(self, otherBill):
        if self.uid != otherBill.uid:
            return False
        
        # same UID might be in different projects ?
        if self.project.uid != otherBill.project.uid:
            return False
        
        return True
    
    def getDatetime(self):
        _dt = datetime.strptime(self.uid, "%Y-%m-%d")
        return _dt
    
    """
    given year must be int
    """
    def isYear(self, year):
        dt = self.getDatetime()
        _year = dt.strftime("%Y")
        return int(_year) == int(year)
    
    # returns datetime time based on multiple possible patterns
    #
    def parse_date(self, s):
        
        FORMATS = ["%Y-%m-%d", "%Y-%m", "%Y"]
        for fmt in FORMATS:
            try:
                dt = datetime.strptime(s, fmt)
                if fmt == "%Y-%m":  # set to last day of month
                    last_day = calendar.monthrange(dt.year, dt.month)[1]
                    return datetime(dt.year, dt.month, last_day)
                if fmt == "%Y":  # set to last day of year
                    return datetime(dt.year, 12, 31)
                return dt
            except ValueError:
                continue
            
        raise ValueError(f"Date '{s}' does not match expected formats")

    # input are strings : "YYYY-MM-DD"
    # input is array [start,end]
    #
    def isDateRangeOverlap(self, range):

        if len(range) <= 0:
            print("error:need range")
            return
        
        start = self.parse_date(range[0])

        if len(range) == 1:
            end = start
        else:
            end = self.parse_date(range[1])

        print(str(self.start)+","+str(self.end)+" ? "+str(start)+","+str(end))

        #if (start >= self.start and start <= self.end) or (end >= self.start and end <= self.end):
        # two ranges overlap if each range starts before the other ends.
        if start <= self.end and self.start <= end:
            return True

        return False
    
    def isDateRange(self, start, end):
        return self.isTimeframe(start, end)
        
    def isTimeframe(self, start, end):
        return self.start >= start and self.end <= end
    
        
    def isSameWeek(self, dt):
        
        _dt = self.getDatetime()
        
        # same year ?
        if _dt.strftime("%Y") != dt.strftime("%Y") :
            return False

        return _dt.strftime("%W") == dt.strftime("%W")
        
    def stringify(self):
        
        _start = self.start.strftime("%Y-%m-%d")
        _end  = self.end.strftime("%Y-%m-%d")

        return self.id+"=>"+_start+","+_end
    
    def isForfait(self):
        return self.forfait != None

    def getLabelDate(self):
        import calendar
        
        sMonth = calendar.month_abbr[int(self.start.strftime("%m"))]
        sMonth += " "+self.start.strftime("%Y")

        eMonth = calendar.month_abbr[int(self.end.strftime("%m"))]
        eMonth += " "+self.end.strftime("%Y")

        return sMonth+" | "+eMonth
    
    # str Ym
    def countDays(self, Ym = None):
        
        if self.isForfait():
            return self.forfait
        
        dYm = None
        if Ym != None:
            dYm = strToYmd(Ym)
        
        output = 0
        for t in self.tasks:
            
            # has filter ? can be null
            if dYm != None:
                if not t.isMonth(dYm):
                    continue
            
            output += t.getTimeSpent()
        
        return output
    
    def getHT(self, Ym=None):
        """
        Compute HT amount.
        If Ym given (YYYY-M string), applies the rate valid at that month's 1st.
        If Ym is None, sums all months with their respective rates.
        Forfait case: single rate at bill start date.
        """
        if self.isForfait():
            return self.forfait * self.project.getTaux(self.start)

        if Ym is not None:
            # Ym is "YYYY-M" or "YYYY-MM" (no day) — add first day for date parsing
            parts = Ym.split("-")
            dt = datetime(int(parts[0]), int(parts[1]), 1)
            return self.countDays(Ym) * self.project.getTaux(dt)

        # total: sum by month with per-month rate
        total = 0.0
        for yr, mo in _iter_months(self.start, self.end):
            m_str = f"{yr}-{mo}"
            dt = datetime(yr, mo, 1)
            total += self.countDays(m_str) * self.project.getTaux(dt)
        return total

    # percentage of TVA to apply
    def getTVA(self):
        return float(self.project.assoc.filterKey("tva"))
    
    def getTvaTotal(self):
        return self.getTVA() * self.getHT()

    def getTTC(self):
        return self.getHT() + self.getTvaTotal() + self.getTransactionsTTC()
    
    def getTransactionsTTC(self):
        output = 0
        for t in self.transactions:
            output += t.solvePrice()
        return round(output, 2)

    def dump(self):
        output = self.project.name+"\n"

        output += f"\nuid         {self.uid}"
        output += f"\ndate range  [{self.start:%Y-%m-%d},{self.end:%Y-%m-%d}]"

        output += "\n"
        output += "\n"
        output += "\nproject total tasks x"+str(len(self.project.tasks))
        output += "\nthis bill tasks x"+str(len(self.tasks))
        for t in self.tasks:    
            output += "\n  "+t.stringify()
        
        output += "\n\nMontant:"
        output += "\n  HT : "+str(self.getHT())
        output += "\n  TTC : "+str(self.getTTC())

        return output
    
    
    def solveFullUid(self):
        
        from packages.database.database import Database

        dt = datetime.strptime(self.uid, "%Y-%m-%d")
        bills = Database.instance.getWeekBills(dt)
        
        week = dt.strftime("%W")

        if self.verbose:
            print("bill?fullUID    dt: "+str(dt)+" , week: "+str(week))
            print("total bills this week : "+str(len(bills)))
        
        # search for this bill index out of ALL possible bills this week
        idx = -1
        for i in range(0,len(bills)):
            
            if self.verbose : print("     #"+str(i)+" ? "+bills[i].uid+" @ "+bills[i].project.uid)
            
            if bills[i].compareBill(self):
                idx = i

        # not found in project
        if idx < 0 :
            print("bill?FUID    "+self.uid+" not found in all bills of week #"+str(week))
            return None
        
        if self.verbose:
            print("bill:    date : "+str(dt)+" match bills x", len(bills))
            print("bill:    searching for local bill : "+self.uid)
            print("bill:    => index #"+str(idx))
        
        # using index within this project has base num
        # must inc because first is index 0
        # index "0" is bill "_01"
        idx += 1

        # leading 0X
        if idx < 10:
            idx = "0"+str(idx)
        else:
            idx = str(idx)
        
        # to Y-m
        trunc = self.uid.split("-")
        trunc = trunc[0]+"-"+trunc[1]
        
        return trunc + "_s"+week+"-"+idx
    
    """
    this will generate the full UID of a bill
    """
    def getFullUid(self):
        
        if self.fullUID == None:
            self.fullUID = self.solveFullUid()
            
        return self.fullUID

    def getTimespanMonths(self):

        cy = int(self.start.strftime("%Y"))
        ey = int(self.end.strftime("%Y"))
        cm = int(self.start.strftime("%m"))
        em = int(self.end.strftime("%m"))

        # print("starts @ "+str(cy)+"-"+str(cm))

        months = []

        safe = 999
        while cy <= ey and safe > 0:
            maxMonth = 12
            
            if cy == ey:
                maxMonth = em
            
            while cm <= maxMonth:
                output = str(cy)+"-"+str(cm)
                months.append(output)
                cm += 1
                safe -= 1
            
            cy += 1
            cm = 1

            safe -= 1

        if safe <= 0:
            print("error:safe")
        
        return months
    
    def log(self, msg):

        if not Bill.verbose:
            return
    
        print("bill#"+self.uid+" : "+msg)


"""
FRAIS ADDITIONNEL
possible additionnal transaction(s) in a bill
ie : frais
"""
class BillTransaction:
    def __init__(self, type, value):
        split = value.split(",")

        self.type = type

        self.label = split[0]

        self.price = 0
        if len(split) > 1:
            self.price = float(split[1])

        self.quantity = 1
        if len(split) > 2:
            self.quantity = float(split[2])

    def solvePrice(self):
        if self.quantity <= 1:
            return self.price
        else:
            return round(self.price * self.quantity, 2)
    
    def getType(self):
        return self.type
