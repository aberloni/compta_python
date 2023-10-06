from library.database import Assoc

class Client:
    def __init__(self, fileName):
        
        #print("client() "+fileName)

        self.assoc = Assoc(fileName)

        self.uid = self.assoc.filterKey("uid")
        self.name = self.assoc.filterKey("name")

        pass
