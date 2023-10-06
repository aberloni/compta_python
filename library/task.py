
from datetime import datetime

class Task:
    def __init__(self, assoc):

        self.key = assoc.key
        self.blob = assoc.value

        # print("task blob : ", self.blob)

        dt = ""
        if assoc.hasValues():
            dt = assoc.values[0]
        else:
            dt = assoc.value

        self.date = datetime.strptime(dt,"%Y-%m-%d")

        self.len = 1
        if assoc.hasValues():
            len = assoc.values[1]
            if "1/2" in len:
                self.len = 0.5
            if "1/4" in len:
                self.len = 0.25
        
        # print(self.stringify())

        pass

    def getProject(self):
        from library.database import Database
        return Database.instance.getProject(self.key)
    
    def getValue(self, uid):
        if not self.hasValues():
            return None
        
        for v in self.values:
            if uid in v:
                return v
        
        # NOT FOUND

        return None
    
    def stringify(self):
        _date = self.date.strftime("%Y-%m-%d")
        return "date:"+_date+" , len:"+str(self.len)

    # YYYY-mm
    def isMonth(self, strYm):
        
        ym = datetime.strptime(strYm, "%Y-%m")
        #_ym = self.date.strftime("%Y-%m")

        # print(str(ym)+" VS "+str(self.date))

        if ym.year != self.date.year:
            return False
        
        if ym.month != self.date.month:
            return False
        
        # print("ok !")
        return True
