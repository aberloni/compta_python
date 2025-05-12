
from packages.database.database import Database, DatabaseType
from packages.database.bill import BillTransaction

from modules.assocs import Assoc

from datetime import datetime

class Project:

    verbose = False
    
    uid = None
    name = None
    
    client = None
    bills = None # array
    
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
    
    # tasks injection in this project
    #
    def assignTasks(self, tasks):
        self.tasks = []
        for t in tasks:
            if t.key == self.uid:
                self.tasks.append(t)
        
        if self.verbose:
            print("project "+self.uid+" was assigned tasks x", len(self.tasks))

        # tasks are ready : solve project bill data
        self.generateBills()

        pass

    def generateBills(self):
        
        from modules.assocs import Assoc
        from packages.database.database import DatabaseType
        from packages.database.bill import Bill

        # init
        path = "bills_"+self.uid
        self.bills = []
        
        # any bill file matching this project ?
        if not Assoc.has(path, DatabaseType.bills):
            print("project @"+self.uid+" has no bills file")
            return
        
        # search for bills linked to this project
        assocs = Assoc(path, DatabaseType.bills)

        bill = None
        for e in assocs.entries: # each key:value lines

            #print("project.assoc :  "+e.key+" = "+e.value)

            # each line is either a bill header
            # or some detail for that bill
            
            #{YYYY-mm-dd} OR {type}
            type = e.key[0] # first symbol of line

            if type.isnumeric(): # starts with a number = new bill
                
                bill = Bill(self, e.key, e.value)
                
                if self.verbose: print("+Bill : "+e.key)
                
                self.bills.append(bill)
                
            else: # lines between each bill header
                
                # additionnal fields for this bill
                
                match e.key:
                    case "Frais":
                        bill.addTransaction(e.key, e.value)
                        
                    case "Label":
                        bill.label = e.value  # override label
                        if self.verbose: print("+Label :     "+bill.label)
                    
                    case "Designation":
                        bill.designation = e.value # override designation
                        if self.verbose: print("+Designation :   "+bill.designation)
                        
        #print("bill : "+self.uid+" , solved x" ,len(self.bills))
                
        
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

    def getBillsInDateRange(self, start, end):
        
        _bills = []
        for b in self.bills:
            if b.isTimeframe(start, end):
                _bills.append(b)
                
        return _bills

    # bill in same week as given date
    #
    def getMatchingWeekBill(self, dateStr):

        date = datetime.strptime(dateStr, "%Y-%m-%d")

        for b in self.bills:
            if b.isSameWeek(date):
                return b
        
        print("NOT FOUND : bill:"+dateStr)
        
        return None

    # return array of bills of same week date
    #
    def getMatchingWeekBills(self, date):
        output = []

        #week = datetime.strptime(date, "%Y-%m-%d")
        #week = week.strftime("%W")

        for b in self.bills:
            if b.isSameWeek(date):
                output.append(b)
        
        if self.verbose and len(output) > 0:
            print("matching.week    project:"+self.uid+" @"+str(date)+" , found project bills x"+str(len(output)))

        return output 
    
    def getTaux(self):
        return int(self.assoc.filterKey("taux"))
