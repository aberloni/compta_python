
import configs
#from modules.system import *
from modules.logger import *
from modules.path import *

"""
a file from the database
that can be parsed as a series of KEY:VALUE,VALUE,VALUE

params :
    dbType is name of any subfolder/ of database/
"""
class Assoc:

    def __init__(self, fileName, dbType = None):
        
        self.fileName = fileName

        if dbType == None:
            return self.create(fileName)
        
        return self.createBySub(fileName, dbType)

    # using LNK
    def createBySub(self, fileName, dbType):
        
        if not configs.dbExtension in fileName:
            fileName = fileName + configs.dbExtension
  
        lines = Path.getLinesFromDbType(dbType, fileName)

        #print(fileName+" QTY ", len(lines))

        self.solveEntries(lines)

    def create(self, fileName):
        if not configs.dbExtension in fileName:
            fileName = fileName + configs.dbExtension
        
        lines = Path.getLinesDbFile(fileName)

        self.solveEntries(lines)
    
    def solveEntries(self, lines):
        
        if lines == None:
            print("error:no lines given Assoc@"+self.fileName)
            return

        self.entries = []

        for i in range(0, len(lines)):
            self.entries.append(AssocEntry(lines[i]))
        
    def filterKeyContains(self, pattern):
        
        for e in self.entries:
            if e.key.lower() in pattern.lower():
                return e
        
        #library.system.warning(pattern+" NOT FOUND")

        return None

    # returns value of that key
    def filterKey(self, key):

        if self.entries == None:
            logError("no entries on Assoc@"+self.fileName)
            return None
        
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
            

"""
key:value
key:value,value,value
"""
class AssocEntry:
    def __init__(self, strData):
        
        if len(strData) <= 0:
            print("error : data is empty")
            return
        
        buff = strData.split(":")
        
        if len(buff) < 2:
            print("error:no value ? "+strData)

        # remove unwanted spaces
        self.key = buff[0].strip()
        self.value = buff[1].strip()
        
        # values[]
        # NEVER single value
        self.values = []
        if "," in self.value:
            self.values = self.value.split(",")
        else:
            self.values.append(self.value)

        pass

    def hasValues(self):
        return len(self.values) > 0
    
    def isKey(self, key):
        
        # print(self.key+" == "+key)

        return self.key == key
