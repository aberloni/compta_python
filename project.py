import database
from bill import Bill
from datetime import datetime

class Project:

    verbose = False

    def __init__(self, fileName):
        
        self.assoc = database.Assoc(fileName)

        self.uid = self.assoc.filterKey("uid")
        self.name = self.assoc.filterKey("name")

        self.client = database.Database.instance.getClient(self.assoc.filterKey("client"))
        # self.tasks = Database.tasks.filterKeys(self.uid)
        
        pass
    
    """
    bills:[2023-09=>2023-08-01,2023-09-31]
    bills:[2023-09=>2023-08-01,2023-09-31];[2023-09=>2023-08-01,2023-09-31]
    """
    def getBillSignatures(self):

        _blob = self.assoc.filterKey("bills")
        
        if _blob != None:
            if _blob.find(";") >= 0:
                _blob = _blob.split(";")
            else:
                _blob = []
                _blob.append(_blob)

        return _blob

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
        
        self.bills = []
        signatures = self.getBillSignatures()
        if signatures != None:
            for s in signatures:
                self.bills.append(Bill(self, s))
            
            #print(self.uid+" has bills x", len(self.bills))

    """
    date must be Y-m-d
    """
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

class Task:
    def __init__(self, assoc):

        self.key = assoc.key
        self.blob = assoc.value

        # print("task blob : ", self.blob)

        dt = ""
        if assoc.hasValues():
            dt = assoc.values[0]
        else:
            dt = assoc.value

        self.date = datetime.strptime(dt,"%Y-%m-%d")

        self.len = 1
        if assoc.hasValues():
            len = assoc.values[1]
            if "1/2" in len:
                self.len = 0.5
            if "1/4" in len:
                self.len = 0.25
        
        # print(self.stringify())

        pass

    def getProject(self):
        return database.Database.instance.getProject(self.key)
    
    def getValue(self, uid):
        if not self.hasValues():
            return None
        
        for v in self.values:
            if uid in v:
                return v
        
        # NOT FOUND

        return None
    
    def stringify(self):
        _date = self.date.strftime("%Y-%m-%d")
        return "date:"+_date+" , len:"+str(self.len)

    # YYYY-mm
    def isMonth(self, strYm):
        
        ym = datetime.strptime(strYm, "%Y-%m")
        #_ym = self.date.strftime("%Y-%m")

        # print(str(ym)+" VS "+str(self.date))

        if ym.year != self.date.year:
            return False
        
        if ym.month != self.date.month:
            return False
        
        # print("ok !")
        return True
