from datetime import datetime
from datetime import timedelta

from modules.system import *

"""
date de facturation:{start},{end}|montant fixe
{math sign}label, prix, quantité
"""

class Bill:
    
    verbose = True

    fullUID = None
    
    def __init__(self, project, uid, billHeader):
        
        # [UID=>START,END]
        self.project = project

        # data = data[1:-1] # remove []

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

    def injectData(self, data):

        # | is to override day count
        if "|" in data:
            splitted = data.split("|")
            data = splitted[0]
            self.forfait = int(splitted[1])

        _dtSplit = data.split(",")

        # real datetime, not strings
        
        self.log("    bill.range : "+_dtSplit[0]+" -> "+_dtSplit[1])

        self.start = datetime.strptime(_dtSplit[0], "%Y-%m-%d")

        # date must be valid
        try:
            self.end = datetime.strptime(_dtSplit[1], "%Y-%m-%d")
        except ValueError:
            print("ERROR : invalid date : ",_dtSplit[1])
            
        self.tasks = []
        for t in self.project.tasks:
            if t.isDateRange(self.start, self.end):
                self.tasks.append(t)

        self.log("    bill.tasks x "+str(len(self.tasks))+" / total in project x "+str(len(self.project.tasks)))

    def parseTransaction(self, assoc):
        self.transactions.append(BillTransaction(assoc.key, assoc.value))
    
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
    
    """
    given year must be int
    """
    def isYear(self, year):
        _dt = datetime.strptime(self.uid, "%Y-%m-%d")
        _year = _dt.strftime("%Y")
        return int(_year) == int(year)
    
    def isSameWeek(self, dt):
        
        # this bill date
        _dt = datetime.strptime(self.uid, "%Y-%m-%d")
        
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

            output += t.len
        return output
    
    def getHT(self, Ym = None):
        return self.countDays(Ym) * self.project.getTaux()

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
        output = self.project.name

        output += "\n\nuid : "+self.uid

        output += "\n\nproject tasks x"+str(len(self.project.tasks))

        output += "\n\nbill tasks x"+str(len(self.tasks))
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
            
            print("     #"+str(i)+" ? "+bills[i].uid+" @ "+bills[i].project.uid)
            
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
    def getBillFullUid(self):
        
        if self.fullUID == None:
            self.fullUID = self.solveFullUid()
            print("=> "+str(self.fullUID))
        
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
    
    def isTimeframe(self, start, end):
        return self.start >= start and self.end <= end
    
    def log(self, msg):

        if not Bill.verbose:
            return
    
        print("bill#"+self.uid+" : "+msg)

    
"""
all lines of a bill
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
