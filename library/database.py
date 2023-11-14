import os
from enum import Enum

import configs
import library.system

from library.assocs import Assoc

DatabaseType = Enum('DatabaseType', ["bills","infos","clients", "projects", "tasks", "statements"])

#db = Database()

class Database:

    verbose = False

    def __init__(self):
        
        Database.instance = self

        pass
        
    @staticmethod
    def tracking():

        instance = Database.billing()

        instance.solveStatements()

        return instance
    
    @staticmethod
    def billing():
        
        # from os import walk

        instance = Database()

        instance.solveClients()
        instance.solveTasks()
        instance.solveProjects()

        return instance

    def solveStatements(self):
        self.statements = self.fetch(DatabaseType.statements)
        #print("imported x", len(self.statements))


    def solveClients(self):

        # -clients
        self.clients = self.fetch(DatabaseType.clients)
    
    def solveProjects(self):

        self.projects = self.fetch(DatabaseType.projects)
        for p in self.projects:
            p.assignTasks(self.tasks)

        # print(self.clients)
        # print(self.projects)
        
        print("imported projects : x", len(self.projects))



    def solveTasks(self):

        from library.task import Task
        from library.path import Path

        # -tasks
        # get folder where tasks are
        taskFiles = Path.getAllFilesFromDbType(DatabaseType.tasks)

        self.tasks = []

        for f in taskFiles:
            
            f = os.path.basename(f) # remove path

            # _tasks = Assoc("tasks.compta", DatabaseSubFolders.tasks)
            _tasks = Assoc(f, DatabaseType.tasks) # get all tasks from this tasks_file

            # add them all
            for t in _tasks.entries:
                self.tasks.append(Task(t))

        if self.verbose:
            print("from tasks files = total tasks[] x", len(self.tasks))

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

    """
    will create an array of matching dbType class
    """
    def fetch(self, dbType):
        
        from library.client import Client
        from library.project import Project
        from library.path import Path
        from library.statements import Statements

        files = Path.getAllFilesFromDbType(dbType)
        # files = self.fetchFiles(dbType)

        output = []
        for c in files:
            tmp = None

            c = os.path.basename(c)
            # remove path
            # c = c[-c.rfind("\\")]

            print("db::fetch("+dbType.name+") @ "+c)

            if dbType == DatabaseType.clients:
                tmp = Client(c)
            elif dbType == DatabaseType.projects:
                tmp = Project(c)
            elif dbType == DatabaseType.statements:
                tmp = Statements(c)
            
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

            # print(p.uid+" & "+str(dt)+" => bills x", len(_bills))

            if len(_bills) > 0:
                for b in _bills:
                    bills.append(b)
        
        return bills

    def countWeekBills(self, dt):
        bills = self.getWeekBills(dt)
        return len(bills)

    def solveUnpaid(self):
        output = []

        for p in self.projects:
            bills = p.getBills()

            

            for b in bills:
                ttc = b.getTTC()

                found = False

                # search for TTC in statements
                for si in self.statements:
                    for s in si:
                        if ttc == s.amount:
                            found = True
            
                if not found:
                    output.append(b)
        
        return output
