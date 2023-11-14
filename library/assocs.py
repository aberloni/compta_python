
import configs
import library.system

# a file from the database
# that can be parsed as a series of KEY:VALUE
#
class Assoc:

    def __init__(self, fileName, sub = None):
        
        self.fileName = fileName;

        if sub == None:
            return self.create(fileName)
        
        return self.createBySub(fileName, sub)

    # using LNK
    def createBySub(self, fileName, sub):

        if not configs.dbExtension in fileName:
            fileName = fileName + configs.dbExtension
        
        lines = library.system.loadFileLnk(sub, fileName)

        self.solveEntries(lines)

    def create(self, fileName):
        if not configs.dbExtension in fileName:
            fileName = fileName + configs.dbExtension
            
        lines = library.system.loadFileDb(fileName)

        self.solveEntries(lines)
    
    def solveEntries(self, lines):
        
        if lines == None:
            print("error:no lines given Assoc@"+self.fileName)
            return

        self.entries = []

        for i in range(0, len(lines)):
            self.entries.append(AssocEntry(lines[i]))
        
    # returns value of that key
    def filterKey(self, key):

        if self.entries == None:
            print("error: no entries on Assoc@"+self.fileName)
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
            

class AssocEntry:
    def __init__(self, strData):
        
        if len(strData) <= 0:
            print("error : data is empty")
            return
        
        buff = strData.split(":")
        
        if len(buff) < 2:
            print("error:no value ? "+strData)

        self.key = buff[0].strip()
        self.value = buff[1].strip()

        self.values = []
        if "," in self.value:
            self.values = self.value.split(",")

        pass

    def hasValues(self):
        return len(self.values) > 0
    
    def isKey(self, key):
        
        # print(self.key+" == "+key)

        return self.key == key
