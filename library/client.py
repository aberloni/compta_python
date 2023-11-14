from library.database import Assoc
from library.database import DatabaseType

class Client:
    def __init__(self, fileName):
        
        #print("client() "+fileName)

        self.assoc = Assoc(fileName, DatabaseType.clients)

        self.uid = self.assoc.filterKey("uid")
        self.name = self.assoc.filterKey("name")

        pass
