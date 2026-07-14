"""
    Credentials of a client
"""
from modules.assocs import Assoc

from packages.database.database import DatabaseType
from packages.database.database import Database

class Client:
    def __init__(self, fileName):
        
        #print("client() "+fileName)

        self.assoc = Assoc(fileName, DatabaseType.clients)

        self.uid = self.assoc.filterKey("uid")
        self.name = self.assoc.filterKey("name")
        self.creditor = self.assoc.filterKey("creditor")
        self.country = (self.assoc.filterKey("country") or "FR").upper()
        self.tva_number = self.assoc.filterKey("tva")

        pass

    def getCountryInfo(self):
        """Return the Assoc for infos/{country}.info (tva rate, invoice mention), or None if not defined."""
        from modules.assocs import Assoc
        from packages.database.database import DatabaseType

        if not Assoc.has(self.country, DatabaseType.infos):
            return None

        return Assoc(self.country, DatabaseType.infos)

    def getBillsInTimeFrame(self, dtStart, dtEnd):
        
        _bills = []
        
        for b in Database.instance.bills:
            if b.isTimeframe(dtStart, dtEnd):
                _bills.append(b)
        
        return _bills

    def getUnpaids(self, dtStart, dtEnd):
        
        _bills = self.getBillsInTimeFrame(dtStart, dtEnd)
        
        for b in _bills:
            print(b.name)
        
        pass
    