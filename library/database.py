import os
from enum import Enum

import configs
import library.system

from library.assocs import Assoc

DatabaseType = Enum('DatabaseType', ["bills","infos","clients", "projects", "tasks"])

class Database:

    verbose = False

    def __init__(self):
        
        from library.task import Task
        from os import walk

        Database.instance = self

        self.clients = self.fetch(DatabaseType.clients)
        
        # get folder where tasks are
        tasksPath = Database.getLnkPathFromType(DatabaseType.tasks)

        print("tasks @ "+tasksPath)

        # get all files over there
        taskFiles = library.system.getAllFilesFromLnk(tasksPath)

        self.tasks = []

        for f in taskFiles:
            
            f = os.path.basename(f) # remove path

            # _tasks = Assoc("tasks.compta", DatabaseSubFolders.tasks)
            _tasks = Assoc(f, DatabaseType.tasks) # get all tasks from this tasks_file

            # add them all
            for t in _tasks.entries:
                self.tasks.append(Task(t))

        if self.verbose:
            print("from tasks files x", len(tasksPath)," = total tasks[] x", len(self.tasks))

        self.projects = self.fetch(DatabaseType.projects)
        for p in self.projects:
            p.assignTasks(self.tasks)

        # print(self.clients)
        # print(self.projects)

        pass

    def getLnkPathFromType(dbType):
        return configs.pathDatabase + dbType.name + ".lnk"
    
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

        files = library.system.getAllFilesFromLnk(configs.pathDatabase + dbType.name + ".lnk")
        # files = self.fetchFiles(dbType)

        output = []
        for c in files:
            tmp = None

            c = os.path.basename(c)
            # remove path
            # c = c[-c.rfind("\\")]

            print("db fetch() @ "+c)

            if dbType == DatabaseType.clients:
                tmp = Client(c)
            elif dbType == DatabaseType.projects:
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

            # print(p.uid+" & "+str(dt)+" => bills x", len(_bills))

            if len(_bills) > 0:
                for b in _bills:
                    bills.append(b)
        
        return bills

    def countWeekBills(self, dt):
        bills = self.getWeekBills(dt)
        return len(bills)



