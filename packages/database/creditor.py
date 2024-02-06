from packages.database.database import DatabaseType
from modules.path import Path
from modules.system import *

class Creditor:
    
    filters = {}
    
    def __init__(self):

        path = Path.getDbTypePath(DatabaseType.creditors)
        #print(path)

        files = getAllFilesInFolder(path)

        #print(files)

        for file in files:
            
            # ie : Z:/path/to/cre/file/resto.cre

            key = file[:-4] # remove ext

            # remove path
            key = key.replace("\\","/") 
            key = key[key.rfind("/")+1:]
            
            self.filters[key] = self.solveContent(file)

        print(self.filters)

    def solveContent(self, file):

        blob = {}

        content = loadFile(file)
        print(content)

        list = []
        for c in content:
            values = []
            if ":" in c:
                values = c.split(":")
            else:
                values.append(c)
            
            list.append(values)

        blob["content"] = list
        blob["location"] = ""

        return blob