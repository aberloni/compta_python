from packages.database.database import DatabaseType
from modules.path import Path
from modules.system import *

class Creditor:
    
    filters = {}
    
    def __init__(self):

        path = Path.getDbTypePath(DatabaseType.creditors)
        #print(path)

        files = getAllFilesInFolder(path)

        print(files)

        # foreach...

