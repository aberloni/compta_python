# https://blog.aspose.com/pdf/create-pdf-files-in-python/

import os
import configs

from enum import Enum
from datetime import datetime

DatabaseType = Enum('DatabaseType', ['client', 'project', 'task'])

def loadFile(fileNameExt):

    path = configs.pathDatabase + fileNameExt

    with open(path, "r", encoding='utf-8') as f:
        lines = f.readlines()

    output = []
    for l in lines:
        
        l = l.strip()

        if len(l) <= 0:
            #print("skipping empty line")
            continue

        if "#" in l:
            #print("skipping comment line")
            continue

        output.append(l)

    return output

def loadFileByDbType(dbType, fileNameExt):
    
    path = configs.pathDatabase+dbType.name+"_"+fileNameExt

    f = open(path, "r")
    lines = f.readlines()

    # Strips the newline character
    for i in range(0, len(lines)):
        lines[i] = lines[i].strip()
    
    # string[]
    return lines



class Assoc:
    def __init__(self, fileName):

        if not configs.dbExtension in fileName:
            fileName = fileName + configs.dbExtension

        lines = loadFile(fileName)

        self.entries = []

        for i in range(0, len(lines)):
            self.entries.append(AssocEntry(lines[i]))
        
        pass

    # returns value of that key
    def filterKey(self, key):
        for e in self.entries:
            if e.isKey(key):
                return e.value
            
        return None
    
    def filterHtmlValue(self, key):
        value = self.filterKey(key)
        return value.replace("|","<br/>")

    # list of all entries with given key
    def filterKeys(self, key):

        output = []
        for i in range(0, len(self.entries)):
            _entry = self.entries[i]

            if _entry.isKey(key):
                output.append(_entry)
        
        if len(output) <= 0:
            print("nothing to return : ", key)
        
        return output
            

class AssocEntry:
    def __init__(self, strData):
        
        if len(strData) <= 0:
            print("error : data is empty")
            return
        
        print(strData)

        buff = strData.split(":")
        
        self.key = buff[0].strip()
        self.value = buff[1].strip()

        self.values = []
        if "," in self.value:
            self.values = self.value.split(",")

        pass

    def hasValues(self):
        return len(self.values) > 0
    
    def isKey(self, key):
        
        # print(self.key+" == "+key)

        return self.key == key

class Client:
    def __init__(self, fileName):
        
        #print("client() "+fileName)

        self.assoc = Assoc(fileName)

        self.uid = self.assoc.filterKey("uid")
        self.name = self.assoc.filterKey("name")

        pass

class Project:

    def __init__(self, fileName):
        
        self.assoc = Assoc(fileName)

        self.uid = self.assoc.filterKey("uid")
        self.name = self.assoc.filterKey("name")

        self.client = Database.instance.getClient(self.assoc.filterKey("client"))
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
        
        print("project "+self.uid+" was assigned tasks x", len(self.tasks))

        self.generateBills()

        pass

    def generateBills(self):
        
        self.bills = []
        signatures = self.getBillSignatures()
        if signatures != None:
            for s in signatures:
                self.bills.append(Bill(self, s))
            print(self.uid+" has bills x", len(self.bills))

    """
    date must be Y-m-d
    """
    def getBill(self, dateStr):

        date = datetime.strptime(dateStr, "%Y-%m-%d")

        # _dt = datetime.strptime(date, "%Y-%m")

        for b in self.bills:
            if b.isSameWeek(date):
                return b
        
        print("bill:"+dateStr+" not found")
        
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
        
        print(self.uid+" ? "+str(date)+" , found bills x"+str(len(output)))

        return output 
    
    def getTaux(self):
        return int(self.assoc.filterKey("taux"))

class Bill:
    def __init__(self, project, data):
        
        # [UID=>START,END]
        self.project = project

        data = data[1:-1] # remove []

        _split = data.split("=>")
        self.uid = _split[0] # 2023-09-XX

        _dtSplit = _split[1]
        _dtSplit = _dtSplit.split(",")

        print(repr(data))

        # real datetime, not strings
        self.start = datetime.strptime(_dtSplit[0], "%Y-%m-%d")
        self.end = datetime.strptime(_dtSplit[1], "%Y-%m-%d")

        self.tasks = []
        for t in project.tasks:
            if t.date > self.start and t.date < self.end:
                self.tasks.append(t)

        print("bill "+self.uid+" tasks x ", len(self.tasks))

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
    
    def getLabelDate(self):
        import calendar
        
        sMonth = calendar.month_abbr[int(self.start.strftime("%m"))]
        sMonth += " "+self.start.strftime("%Y")

        eMonth = calendar.month_abbr[int(self.end.strftime("%m"))]
        eMonth += " "+self.end.strftime("%Y")

        return sMonth+" | "+eMonth
    
    def countDays(self):
        output = 0
        for t in self.tasks:
            output += t.len
        return output
    
    def getHT(self):
        return self.countDays() * self.project.getTaux()

    def getTVA(self):
        return float(self.project.assoc.filterKey("tva"))
    
    def getTvaTotal(self):
        return self.getTVA() * self.getHT()

    def getTTC(self):
        return self.getHT() + self.getTvaTotal()
    
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
        
        dt = datetime.strptime(self.uid, "%Y-%m-%d")
        bills = Database.instance.getWeekBills(dt)

        print("now found bills x", len(bills))

        inc = -1

        print("searching for local bill : "+self.uid)

        for i in range(0,len(bills)):
            print("  "+bills[i].uid)
            if bills[i].uid == self.uid:
                inc = i

        if inc < 0:
            return None

        print(inc)

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
        return Database.instance.getProject(self.key)
    
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

class Database:
    def __init__(self):
        Database.instance = self

        self.clients = self.fetch(DatabaseType.client)
        
        self.tasks = []
        _tasks = Assoc("tasks.compta")
        for t in _tasks.entries:
            self.tasks.append(Task(t))

        print("total tasks[] x", len(self.tasks))

        self.projects = self.fetch(DatabaseType.project)
        for p in self.projects:
            p.assignTasks(self.tasks)

        # print(self.clients)
        # print(self.projects)

        pass

    def getClient(self, id):

        if not hasattr(self, "clients"):
            print("no clients[]?")
            return None

        for p in self.clients:
            if(p.uid == id):
                return p
        
        print("no #"+id)


    def getProject(self, projectId):

        if not hasattr(self, "projects"):
            print("no projects[]?")
            return None

        for p in self.projects:
            if(p.name == projectId):
                return p
        
        print("no project "+projectId)

    def fetch(self, dbType):
        
        files = self.fetchFiles(dbType)

        output = []
        for c in files:
            tmp = None

            if dbType == DatabaseType.client:
                tmp = Client(c)
            elif dbType == DatabaseType.project:
                tmp = Project(c)
            
            if c != None:
                output.append(tmp)

        # print("loaded "+dbType.name+" x"+str(len(output)))
        return output


    def fetchFiles(self, dbType):
        # self.clients
        output = []

        # files[] contains only file name, not path
        files = os.listdir(configs.pathDatabase)
        for f in files:
            if dbType.name in f:
                output.append(f)
        
        return output

    def getWeekBills(self, dt):
        
        bills = []
        for p in self.projects:
            _bills = p.getWeekBills(dt)
            if len(_bills) > 0:
                for b in _bills:
                    bills.append(b)
        
        return bills

    def countWeekBills(self, dt):
        bills = self.getWeekBills(dt)
        return len(bills)



