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
DatabaseType = Enum('DatabaseType', ["bills", "infos", "clients", "projects", "tasks", "statements", "creditors", "wiring"])

class Database:

    verbose = False

    clients = None
    tasks = None
    projects = None
    
    def __init__(self):
        
        Database.instance = self

        pass
    
    def init_all():
        """Load clients, tasks, projects, creditor, and statements."""
        instance = Database()

        instance.clients = instance.fetch_clients()
        instance.tasks = instance.fetch_tasks()

        instance.fetch_projects()

        Creditor()
        Statements()

        return instance

    @staticmethod
    def init_labels():
        """Load creditor and statements only (for main_labels.py / main_unpaid.py)."""
        instance = Database()

        Creditor()
        Statements()

        return instance

    @staticmethod
    def init_billing():
        """Load clients, tasks, and projects (standard billing run)."""
        instance = Database()

        instance.clients = instance.fetch_clients()
        instance.tasks = instance.fetch_tasks()
        instance.fetch_projects()

        return instance

    def fetch_tasks(self):
        """Load all task entries from every .task file, returning a flat Task list."""
        import packages.database.task as task
        from modules.path import Path
        from modules.assocs import Assoc

        # -tasks
        # get folder where tasks are
        taskFiles = Path.getAllFilesFromDbType(DatabaseType.tasks)

        output = []

        for f in taskFiles:

            f = os.path.basename(f) # remove path

            # extract YYYY-MM context from filename "tasks_2026-01.compta"
            import re as _re
            _m = _re.search(r'(\d{4}-\d{2})', f)
            month_ctx = _m.group(1) if _m else None

            _tasks = Assoc(f, DatabaseType.tasks) # get all tasks from this tasks_file

            # add them all
            for t in _tasks.entries:
                _t = task.Task(t, month_ctx)
                if _t.key is not None:
                    output.append(_t)
        
        if self.verbose:
            print("from tasks files = total tasks[] x", len(output))

        return output

    def getClient(self, id):
        """Return the Client with matching uid, or None."""
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
        """Return the Project with matching uid, or None."""
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
        """Load all Client objects from the clients/ folder."""
        from packages.database.client import Client
        
        files = Path.getAllFilesFromDbType(DatabaseType.clients)
        output = []
        for c in files:
            tmp = Client(os.path.basename(c))
            if c != None:
                output.append(tmp)
        
        return output

    def fetch_projects(self):
        """Load all Project objects, assigning tasks and generating bills."""
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
        

    def getWeekBills(self, date):
        """Return all bills across all projects that share the same week as `date`."""
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
        """Return the count of bills in the same week as `dt`."""
        bills = self.getWeekBills(dt)
        return len(bills)
    
    @staticmethod
    def folderExportStatements():
        return Path.getExportFolderPath()+"statements/"

    @staticmethod
    def folderExportBilling():
        return Path.getExportFolderPath()+"billings/"
