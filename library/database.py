import os
from enum import Enum

import configs
import library.system


DatabaseType = Enum('DatabaseType', ['client', 'project', 'task'])

class Assoc:
    def __init__(self, fileName):

        if not configs.dbExtension in fileName:
            fileName = fileName + configs.dbExtension

        lines = library.system.loadFile(fileName)

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
        
        buff = strData.split(":")
        
        if len(buff) < 2:
            print("error:no value ? "+strData)

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

class Database:

    verbose = False

    def __init__(self):
        
        from library.task import Task

        Database.instance = self

        self.clients = self.fetch(DatabaseType.client)
        
        self.tasks = []
        _tasks = Assoc("tasks.compta")
        for t in _tasks.entries:
            self.tasks.append(Task(t))

        if self.verbose:
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
        
        if self.verbose:
            print("no #"+id)


    def getProject(self, projectUid):

        if not hasattr(self, "projects"):
            
            if self.verbose:
                print("no projects[]?")
            
            return None

        for p in self.projects:
            if(p.uid == projectUid):
                return p
        
        
        if self.verbose:
            print("no project # "+projectUid)

    def fetch(self, dbType):
        
        from library.client import Client
        from library.project import Project

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

            print(p.uid+" & "+str(dt)+" => bills x", len(_bills))

            if len(_bills) > 0:
                for b in _bills:
                    bills.append(b)
        
        return bills

    def countWeekBills(self, dt):
        bills = self.getWeekBills(dt)
        return len(bills)



