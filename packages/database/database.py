import os
from enum import Enum

import configs

from modules.path import Path

DatabaseType = Enum('DatabaseType', ["bills", "infos","clients", "projects", "tasks", "statements", "creditors"])

class Database:

    verbose = False

    def __init__(self):
        
        Database.instance = self

        pass
        
    @staticmethod
    def getExportStatementsFolder():
        return Path.getExportFolderPath()+"statements/"

    @staticmethod
    def getExportBillingFolder():
        return Path.getExportFolderPath()+"billings/"


    """
    database init   : labels
    """
    @staticmethod
    def init_labels():

        from packages.database.creditor import Creditor
        
        instance = Database()

        instance.creditors = Creditor() # all labels to match statem transactions
        instance.fetch_statements() # bank statements
        
        #print("imported x", len(instance.statements))
        
        return instance
    
    """
    database init   : billing
    """
    @staticmethod
    def init_billing():
        
        # from os import walk

        instance = Database()

        instance.fetch_clients()
        instance.solveTasks()
        instance.solveProjects()

        return instance
    
    def solveProjects(self):
        
        #self.solveClients()

        self.fetch_projects()
        
        for p in self.projects:
            p.assignTasks(self.tasks)

        # print(self.clients)
        # print(self.projects)
        
        #print("imported projects : x", len(self.projects))



    def solveTasks(self):

        import packages.database.task as task
        from modules.path import Path
        from modules.assocs import Assoc

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
                self.tasks.append(task.Task(t))

        if self.verbose:
            print("from tasks files = total tasks[] x", len(self.tasks))

    def getClient(self, id):

        if not hasattr(self, "clients"):
            print("no clients[]?")
            return None

        if self.clients is None:
            print("clients[] is None ?")
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



    def fetch_clients(self):
        from packages.database.client import Client
        
        files = Path.getAllFilesFromDbType(DatabaseType.clients)
        output = []
        for c in files:
            tmp = Client(os.path.basename(c))
            if c != None:
                output.append(tmp)
        
        self.clients = output

    def fetch_projects(self):
        from packages.database.project import Project
        files = Path.getAllFilesFromDbType(DatabaseType.projects)
        output = []
        for c in files:
            tmp = Project(os.path.basename(c))
            if c != None:
                output.append(tmp)
        
        self.projects = output
        
    def fetch_statements(self):
        from packages.database.statements import BankLogs
        import modules.system
        
        # files = Path.getAllFilesFromDbType(DatabaseType.statements)
        
        output = []
        
        path = Path.getDbTypePath(DatabaseType.statements)
        #print(path)
        
        bankFolders = modules.system.getAllFilesInFolder(path)
        for b in bankFolders:
            
            b = b + "/"
            print(b)
            
            files = modules.system.getAllFilesInFolder(b)
            if len(files) <= 0:
                print(" ? no statements files in folder : "+b)
                continue
            
            print("x"+str(len(files)))
            
            for filePath in files:
                
                # print(b+" >> "+c)
                tmp = BankLogs(filePath)
                output.append(tmp)
        
        print("statements x"+str(len(output)))
        
        self.statements = output
        
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
