"""
    Meant to fetch/encapsulate all data from DB/

    Accessible using :      Database.instance

"""

import os
from enum import Enum

import configs

from modules.path import Path

# define : database enum
DatabaseType = Enum('DatabaseType', ["bills", "infos","clients", "projects", "tasks", "statements", "creditors"])

class Database:

    verbose = False

    def __init__(self):
        
        Database.instance = self

        pass
        

    """
    database init   : labels
    """
    @staticmethod
    def init_labels():

        from packages.database.creditor import Creditor
        
        instance = Database()

        instance.creditors = Creditor() # all labels to match statem transactions
        instance.statements = instance.fetch_statements() # bank statements
        
        #print("imported x", len(instance.statements))
        
        return instance
    
    """
    database init   : billing
        clients
        tasks
        projects
    """
    @staticmethod
    def init_billing():
        
        # from os import walk

        instance = Database()

        instance.clients = instance.fetch_clients() # self.clients
        
        instance.tasks = instance.fetch_tasks()
        instance.projects = instance.fetch_projects()
        
        for p in instance.projects:
            p.assignTasks(instance.tasks)
        
        return instance

    """
        extract all self.tasks
    """
    def fetch_tasks(self):

        import packages.database.task as task
        from modules.path import Path
        from modules.assocs import Assoc

        # -tasks
        # get folder where tasks are
        taskFiles = Path.getAllFilesFromDbType(DatabaseType.tasks)

        output = []

        for f in taskFiles:
            
            f = os.path.basename(f) # remove path

            # _tasks = Assoc("tasks.compta", DatabaseSubFolders.tasks)
            _tasks = Assoc(f, DatabaseType.tasks) # get all tasks from this tasks_file

            # add them all
            for t in _tasks.entries:
                output.append(task.Task(t))

        if self.verbose:
            print("from tasks files = total tasks[] x", len(output))

        return output

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



    """
        returns :   clients[]
    """
    def fetch_clients(self):
        from packages.database.client import Client
        
        files = Path.getAllFilesFromDbType(DatabaseType.clients)
        output = []
        for c in files:
            tmp = Client(os.path.basename(c))
            if c != None:
                output.append(tmp)
        
        return output

    def fetch_projects(self):
        from packages.database.project import Project
        files = Path.getAllFilesFromDbType(DatabaseType.projects)
        output = []
        for c in files:
            tmp = Project(os.path.basename(c))
            if c != None:
                output.append(tmp)
        
        return output
        
    def fetch_statements(self):
        from packages.database.statements import BankLogs
        import modules.system
        
        # path to statements/
        path = Path.getDbTypePath(DatabaseType.statements)
        #print(path)
        
        _bankLogs = []

        # each bank folders within statements
        bankFolders = modules.system.getAllFilesInFolder(path)
        for b in bankFolders:
            
            b = b + "/"
            print("bank : "+b)
            
            # each statements files for a given bank
            files = modules.system.getAllFilesInFolder(b)
            if len(files) <= 0:
                print(" ? no statements files in folder : "+b)
                continue
            
            print("found x"+str(len(files))+" files")
            
            for filePath in files:
                
                # print(b+" >> "+c)
                tmp = BankLogs(filePath)
                _bankLogs.append(tmp)
        
        print("total bank logs x"+str(len(_bankLogs)))

        # for each line within banklogs
        # adds uniq statements (won't be ordered by date)
        output = []
        for b in _bankLogs:
            for s in b.statements:
                if not self.hasStatement(s):
                    output.append(s)

        return output
        
    def hasStatement(self, st):
        for s in self.statements:
            if s.compare(st): return True
        return False
        
    def fetchFiles(self, dbType):
        # self.clients
        output = []

        # files[] contains only file name, not path
        files = os.listdir(configs.pathDatabase)
        for f in files:
            if dbType.name in f:
                output.append(f)
        
        return output

    # returns all bills of same week in date
    # 
    def getWeekBills(self, dt):
        
        bills = []
        for p in self.projects:
            
            # get all bills from that project that are in the same given week
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

    
    @staticmethod
    def folderExportStatements():
        return Path.getExportFolderPath()+"statements/"

    @staticmethod
    def folderExportBilling():
        return Path.getExportFolderPath()+"billings/"
