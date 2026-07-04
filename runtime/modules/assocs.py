
import configs
from modules.system import *
from modules.logger import *
from modules.path import *

def _db_ext(dbType):
    if dbType is None:
        return ".compta"
    return configs.DB_EXTENSIONS.get(dbType.name, ".compta")

class Assoc:
    """Parses a .compta file into AssocEntry[] (key:value lines)."""

    def __init__(self, fileName, dbType = None):
        
        self.fileName = fileName

        if dbType == None:
            return self.create(fileName)
        
        return self.createBySub(fileName, dbType)

    @staticmethod
    def has(fileName, dbType = None):
        """Return True if the file exists in the given dbType folder."""
        ext = _db_ext(dbType)
        if ext not in fileName:
            fileName = fileName + ext

        path = Path.getDbTypePath(dbType)

        return hasFile(path + fileName)

        
        
    def createBySub(self, fileName, dbType):
        """Load entries from a typed subfolder file (e.g. clients/, tasks/)."""
        ext = _db_ext(dbType)
        if ext not in fileName:
            fileName = fileName + ext
  
        lines = Path.getLinesFromDbType(dbType, fileName)

        #print(fileName+" QTY ", len(lines))

        self.solveEntries(lines)

    def create(self, fileName):
        """Load entries from a file in the root database path (no subfolder)."""
        if not any(ext in fileName for ext in configs.DB_EXTENSIONS.values()):
            fileName = fileName + ".compta"
        
        lines = Path.getLinesDbFile(fileName)

        self.solveEntries(lines)
    
    def solveEntries(self, lines):
        """Parse raw lines into self.entries (AssocEntry[])."""
        if lines == None:
            print("error:   'None' lines given  @"+self.fileName)
            return

        self.entries = []
        
        if len(lines) <= 0:
            print("warning:no lines     @"+self.fileName)
            return
        
        for i in range(0, len(lines)):
            line = lines[i].strip()
            if not line or line.startswith("#"):
                continue
            self.entries.append(AssocEntry(lines[i]))
        
    def filterKeyContains(self, pattern):
        """Return first entry whose key is a substring of pattern."""
        for e in self.entries:
            if e.key.lower() in pattern.lower():
                return e
        
        #library.system.warning(pattern+" NOT FOUND")

        return None

    def filterKey(self, key):
        """Return the value of the first entry matching key, or None."""
        if self.entries == None:
            logError("no entries on Assoc@"+self.fileName)
            return None
        
        for e in self.entries:
            if e.isKey(key):
                return e.value
            
        return None
    
    def filterHtmlValue(self, key):
        """Return value with '|' replaced by '<br/>' for HTML rendering."""
        value = self.filterKey(key)
        return value.replace("|","<br/>")

    def filterKeys(self, key):
        """Return all entries matching key as a list."""
        output = []
        for i in range(0, len(self.entries)):
            _entry = self.entries[i]

            if _entry.isKey(key):
                output.append(_entry)
        
        if len(output) <= 0:
            print("nothing to return : ", key)
        
        return output
            

class AssocEntry:
    """One parsed line: key, value (str), values (list split on ',')."""

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
        """True if values list is non-empty."""
        return len(self.values) > 0

    def isKey(self, key):
        """True if this entry's key matches exactly."""
        return self.key == key
