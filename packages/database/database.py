"""
    Meant to fetch/encapsulate all data from DB/

    Accessible using :      Database.instance

"""

import os
from enum import Enum

import configs

from modules.path import Path

from packages.database.creditor import Creditor
from packages.database.statements import Statements

# define : database enum
DatabaseType = Enum('DatabaseType', ["bills", "infos","clients", "projects", "tasks", "statements", "creditors"])

class Database:

    verbose = False

    clients = None
    tasks = None
    projects = None
    
    def __init__(self):
        
        Database.instance = self

        pass
    
    def init_all():
        
        instance = Database()
        
        instance.clients = instance.fetch_clients()
        instance.tasks = instance.fetch_tasks()
        
        instance.fetch_projects()
        
        Creditor()
        Statements()
        
        return instance

    """
    database init   : labels
    """
    @staticmethod
    def init_labels():

        instance = Database()

        Creditor()
        Statements()
        
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
        instance.fetch_projects()
        
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
        
        self.projects = []
        
        for c in files:
            tmp = Project(os.path.basename(c))
            if c != None:
                self.projects.append(tmp)
        
        # tasks is setup : init bills
        if self.tasks != None:
            # for each project : inject tasks
            # to provide data to generate bills
            for p in self.projects:
                p.assignTasks(self.tasks)
        
        return self.projects
        
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
    def getWeekBills(self, date):
        
        bills = []
        for p in self.projects:
            
            # get all bills from that project that are 
            # in the same given week
            _bills = p.getMatchingWeekBills(date)
            
            if len(_bills) <= 0: 
                continue
            
            # append
            for b in _bills:
                bills.append(b)
        
        return bills

    def countWeekBills(self, dt):
        bills = self.getWeekBills(dt)
        return len(bills)
    
    @staticmethod
    def folderExportStatements():
        return Path.getExportFolderPath()+"statements/"

    @staticmethod
    def folderExportBilling():
        return Path.getExportFolderPath()+"billings/"
