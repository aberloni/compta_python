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
            
            if key == "misc": # edge case
                content = loadFile(file)
                for c in content:
                    values = c.split(":")
                    key = values[0]
                    val = values[1]
                    
                    if type(val) != list:
                        val = [val]
                    
                    # key:val
                    self.filters[key] = val
            else: # normal flow, each files
                content = self.solveContent(file)
                print(content)
                self.filters[key] = content

        print("filters x", len(self.filters))
        for k in self.filters:
            print(k)
            print(self.filters[k])

    def solveContent(self, file):

        content = loadFile(file)

        list = []
        for c in content:
            values = []
            if "," in c:
                values = c.split(",")
            else:
                values.append(c)
            
            list.append(values)
        
        return list