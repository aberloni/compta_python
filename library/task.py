import library.system
from datetime import datetime

"""
project:work_date
project:work_date,>redirect_month
project:work_date,1/2 1/4
"""

class Task:

    verbose = False

    def __init__(self, assoc):

        self.key = assoc.key
        self.blob = assoc.value

        # print("task blob : ", self.blob)

        dt = ""
        if not assoc.hasValues():
            print("!w task assoc has no values ?")
        else:
            dt = assoc.values[0]
        
        self.date = library.system.strToYmd(dt)

        # default values
        self.len = 1
        self.redirect = None

        # overrides
        if assoc.hasValues():
            for val in assoc.values:

                if "/" in val:
                    if "1/2" in val:
                        self.len = 0.5
                    if "1/4" in val:
                        self.len = 0.25
                    if "1/0" in val:
                        self.len = 0

                if ">" in val:
                    # https://stackoverflow.com/questions/663171/how-do-i-get-a-substring-of-a-string-in-python
                    self.redirect = val[1:] # remove '>'
                    self.redirect = library.system.strToYmd(self.redirect)
            
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
    
    # output DATETIME
    def getRedirectedDate(self):
        if self.redirect == None:
            return self.date
        else:
            return self.redirect

    # datetime YYYY-mm
    def isMonth(self, dateYm):
        
        dt = self.getRedirectedDate()

        if dateYm.year != dt.year:
            return False
        
        if dateYm.month != dt.month:
            return False
        
        # print("ok !")
        return True
    
    # datetime YYYY-mm-dd
    def isDate(self, dateYmd):

        # print(str(ym)+" VS "+str(self.date))
        dt = self.getRedirectedDate()

        if dateYmd.year != dt.year:
            return False
        
        if dateYmd.month != dt.month:
            return False
        
        if dateYmd.day != dt.day:
            return False
        
        return True
    
    def isDateRange(self, start, end):

        dt = self.getRedirectedDate()

        self.log(str(dt)+" VS ["+str(start)+","+str(end)+"]")

        if dt < start:
            self.log("<<")
            return False
        
        if dt > end :
            self.log(">>")
            return False
        
        self.log("ok")

        return True

    def stringify(self):
        return "date:"+str(self.date)+" (redirect?"+str(self.getRedirectedDate())+") , len:"+str(self.len)
    
    def log(self, msg):

        if not self.verbose:
            return
        
        print(self.key+" ? "+msg)
    