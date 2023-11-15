

from library.bill import Bill
from datetime import datetime

class Project:

    verbose = False

    def __init__(self, fileName):
        
        from library.database import Assoc
        from library.database import Database
        from library.database import DatabaseType

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
        
        from library.database import Assoc
        from library.database import DatabaseType
        self.bills = []
        
        assocs = Assoc("bills_"+self.uid, DatabaseType.bills)

        bill = None
        for e in assocs.entries:

            #{YYYY-mm-dd} OR {type}
            type = e.key[0] # first symbol of line

            if type.isnumeric(): # a bill
                bill = Bill(self, e.key, e.value)
                self.bills.append(bill)
            else: # additionnal fields
                bill.parseTransaction(e)

        #print("bill : "+self.uid+" , solved x" ,len(self.bills))
                
        

    def getBill(self, dateStr):

        date = datetime.strptime(dateStr, "%Y-%m-%d")

        # _dt = datetime.strptime(date, "%Y-%m")

        for b in self.bills:
            if b.isSameWeek(date):
                return b
        
        print("NOT FOUND : bill:"+dateStr)
        
        return None

    def getBills(self):
        return self.bills

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
