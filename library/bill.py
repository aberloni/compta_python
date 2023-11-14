from datetime import datetime
from datetime import timedelta

"""
date de facturation:{start},{end}|montant fixe
{math sign}label, prix, quantité
"""

class Bill:
    
    verbose = False

    def __init__(self, project, uid, billHeader):
        
        # [UID=>START,END]
        self.project = project

        # data = data[1:-1] # remove []

        self.uid = uid # 2023-09-XX

        # https://stackoverflow.com/questions/6871016/adding-days-to-a-date-in-python

        self.limit = datetime.strptime(self.uid, "%Y-%m-%d")
        self.limit = self.limit + timedelta(days=30)
        
        self.limit = self.limit.strftime("%Y-%m-%d")
        
        # forfait is | after dates
        self.forfait = None

        self.transactions = []

        self.injectData(billHeader)

    def injectData(self, data):

        if "|" in data:
            splitted = data.split("|")
            data = splitted[0]
            self.forfait = int(splitted[1])

        _dtSplit = data.split(",")

        # real datetime, not strings
        self.start = datetime.strptime(_dtSplit[0], "%Y-%m-%d")
        self.end = datetime.strptime(_dtSplit[1], "%Y-%m-%d")

        self.tasks = []
        for t in self.project.tasks:
            if t.date >= self.start and t.date <= self.end:
                self.tasks.append(t)

        if self.verbose:
            print("bill#"+self.uid+", init = tasks x ", len(self.tasks))

    def parseTransaction(self, assoc):
        self.transactions.append(BillTransaction(assoc.key, assoc.value))
    
    def hasTransactions(self):
        return len(self.transactions) > 0
            

    def compareBill(self, otherBill):
        if self.uid != otherBill.uid:
            return False
        
        if self.project.uid != otherBill.project.uid:
            return False
        
        return True
    
    def isSameWeek(self, dt):
        # input = datetime.strftime(str(y)+"-"+str(m), "%Y-%m")
        # print(self.uid)
        _dt = datetime.strptime(self.uid, "%Y-%m-%d")
        _week = _dt.strftime("%W")

        week = dt.strftime("%W")
        return _week == week
        
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
    
    def countDays(self, Ym = None):
        
        if self.isForfait():
            return self.forfait
        
        output = 0
        for t in self.tasks:
            
            if Ym != None:
                if not t.isMonth(Ym):
                    continue

            output += t.len
        return output
    
    def getHT(self, Ym = None):
        return self.countDays(Ym) * self.project.getTaux()

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
    
    def getBillFullUid(self):
        
        from library.database import Database

        dt = datetime.strptime(self.uid, "%Y-%m-%d")
        bills = Database.instance.getWeekBills(dt)

        inc = -1
        
        for i in range(0,len(bills)):
            
            #print("#"+str(i)+" ? "+bills[i].uid+" vs "+self.uid)

            if bills[i].compareBill(self):
                inc = i

        if self.verbose:
            print(str(dt.year)+"-"+str(dt.month)+" => found TOTAL bills x", len(bills))
            print("searching for local bill : "+self.uid)
            print("index #"+str(inc))

        if inc < 0:
            return None

        # must inc because first is index 0
        inc += 1

        if inc < 10:
            inc = "0"+str(inc)
        else:
            inc = str(inc)
        
        week = dt.strftime("%W")

        # to Y-m
        trunc = self.uid.split("-")
        trunc = trunc[0]+"-"+trunc[1]
        return trunc + "_s"+week+"-"+inc

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
