from packages.database.database import DatabaseType
from modules.path import Path
from modules.system import *

"""
    wrapper around all .cred files
    gather all labels sorted by keys

    misc.cred     --> label:category,info
    category.cred --> label,info

    this object contains all labels to match statements lines
"""
class Creditor:
    
    verbose = False
    
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
                
                self.solveMisc(file)
                
            else: # normal flow, each files
                self.solveContent(file, key)

        if self.verbose:
            print("filters x", len(self.filters))
            for k in self.filters:
                print("    #"+k)
                print(self.filters[k])

    """
    give a statement label returns matching creditor uid
    """
    def solveCreditorOfLabel(self, labels):
        
        if type(labels) is not list:
            print("labels must be a list[]")
            return None
        
        if len(labels) <= 0:
            print("given statement label is empty | null ?")
            return None
        
        for label in labels:
            label = label.lower()
            
            # print("checking "+statementLabel+" against x"+str(len(self.filters))+" filters");
            
            for uid in self.filters: 
                
                filter = self.filters[uid]
                # print(filter)
                #print(type(filter))
                
                if filter.match(label):
                    return uid
        
        return None

    """
    edge case key:value
    """
    def solveMisc(self, file):
        
        content = loadFile(file)
        
        for c in content:
            values = c.split(":")
            key = values[0]
            val = values[1]
            
            # make sure it's a list
            if type(val) != list:
                val = [val]
            
            self.appendLabel(key, val)

    """
    extract content for file=key & content is values
    """
    def solveContent(self, file, key):
        lines = loadFile(file)
        
        for l in lines:
            if "#" in l:
                continue

            self.appendLabel(key, l)
        
    """
    manage non-existing keys
    and append value/label to it
    """
    def appendLabel(self, key, label):
        
        # not yet in filters
        if not key in self.filters:
            self.filters[key] = CreditorFilter(key, [])
        
        # add label to filter
        self.filters[key].append(label)

"""
entries from a file
has a creditor uid
and all labels matching that uid
"""
class CreditorFilter:
    def __init__(self, key, values):
        self.uid = key
        
        self.labels = []
        for v in values:
            self.append(v)
        
    
    def match(self, label):
        
        for l in self.labels:
            if l.match(label):
                return True
        
        return False
    
    def append(self, label):
        self.labels.append(CreditorFilterEntry(label))

"""
all values assocs with a filter's entry
"""
class CreditorFilterEntry:
    def __init__(self, values):

        if type(values) is list:
            self.values = values
        else:
            self.values = values.split(",")
        
        self.label = self.values[0].lower()
        #self.maps
        
    def match(self, label):
        
        label = label.lower()
        
        # "in" (contains)
        result = self.label in label
        
        #print(self.label+" >> is in : "+label+" ? "+str(result))
        return result