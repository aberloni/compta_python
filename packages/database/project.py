
from packages.database.database import Database, DatabaseType
from packages.database.bill import BillTransaction

from modules.assocs import Assoc

from datetime import datetime


class Project:

    uid = None
    verbose = False
    
    label = "" # label of presation (with days count)

    def __init__(self, fileName):
        
        self.assoc = Assoc(fileName, DatabaseType.projects)

        self.uid = self.assoc.filterKey("uid")
        self.name = self.assoc.filterKey("name")
        
        self.client = Database.instance.getClient(self.assoc.filterKey("client"))
        # self.tasks = Database.tasks.filterKeys(self.uid)
        
        pass
    
    def dump(self):

        print("=== dump ===")
        print(self.uid, " tasks[] ", len(self.tasks))
        
        for t in self.tasks:
            print(t.stringify())

        for b in self.bills:
            print(b.stringify())
        
        print("======")
        pass
    
    def assignTasks(self, tasks):
        self.tasks = []
        for t in tasks:
            if t.key == self.uid:
                self.tasks.append(t)
        
        if self.verbose:
            print("project "+self.uid+" was assigned tasks x", len(self.tasks))

        self.generateBills()

        pass

    def generateBills(self):
        
        from modules.assocs import Assoc
        from packages.database.database import DatabaseType
        from packages.database.bill import Bill

        self.bills = []
        
        path = "bills_"+self.uid
        #print(path)

        assocs = Assoc(path, DatabaseType.bills)

        print("bill file #"+path)
        
        bill = None
        for e in assocs.entries: # each key:value lines

            print(e.key)
            print(e.value)

            #{YYYY-mm-dd} OR {type}
            type = e.key[0] # first symbol of line

            if type.isnumeric(): # starts with a number = a new bill
                
                bill = Bill(self, e.key, e.value)
                self.bills.append(bill)
                
            else:
                
                # additionnal fields
                
                match e.key:
                    case "Label":
                        bill.label = e.value
                    case "Frais":
                        bill.transactions.append(BillTransaction(e.key, e.value))
                        

        #print("bill : "+self.uid+" , solved x" ,len(self.bills))
                
        

    def getBill(self, dateStr):

        date = datetime.strptime(dateStr, "%Y-%m-%d")

        # _dt = datetime.strptime(date, "%Y-%m")

        for b in self.bills:
            if b.isSameWeek(date):
                return b
        
        print("NOT FOUND : bill:"+dateStr)
        
        return None

    """
    given years must be array of int
    """
    def getBills(self, filterYears = None):
        
        if filterYears == None:
            return self.bills
        
        ret = []
        
        for b in self.bills:
            for y in filterYears:
                if b.isYear(y) :
                    ret.append(b)
                
        return ret

    def getWeekBills(self, date):
        output = []

        #week = datetime.strptime(date, "%Y-%m-%d")
        #week = week.strftime("%W")

        for b in self.bills:
            if b.isSameWeek(date):
                output.append(b)
        
        if self.verbose:
            print(self.uid+" ? "+str(date)+" , found bills x"+str(len(output)))

        return output 
    
    def getTaux(self):
        return int(self.assoc.filterKey("taux"))
