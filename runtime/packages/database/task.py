from modules.system import *

"""
project:work_date
project:work_date,>redirect_month
project:work_date,1/2 1/4

project:work_date,"some label to display"

"""

class Task:

    verbose = False

    key = None
    blob = None
    label = ""

    def __init__(self, assoc):

        self.key = assoc.key        # project
        self.blob = assoc.value     # values

        # print("task blob : ", self.blob)

        dt = ""
        if not assoc.hasValues():
            print("!w task assoc has no values ?")
        else:
            dt = assoc.values[0]
        
        self.date = strToYmd(dt)

        # default values
        self.len = 1
        self.redirect = None

        # overrides, comma separator
        if assoc.hasValues():
            for val in assoc.values:
                
                if val == "0": self.len = 0; continue

                if "." in val: # [0,1]%

                    if val == "0.0": self.len = 0
                    elif val == "0.5": self.len = 0.5
                    elif val == "0.25": self.len = 0.25
                    elif val == "0.75": self.len = 0.75

                elif "/" in val: # 1/2 1/4 1/5
                    sides = val.split("/")
                    sides[0] = int(sides[0])
                    sides[1] = int(sides[1])

                    if sides[1] == 0: self.len = 0
                    else: self.len = sides[0] / sides[1]

                elif ">" in val:
                    # https://stackoverflow.com/questions/663171/how-do-i-get-a-substring-of-a-string-in-python
                    self.redirect = val[1:] # remove '>'
                    self.redirect = strToYmd(self.redirect)
                    
                elif "\"" in val:
                    val = val[1:] # remove first "
                    val = val[:-1] # remove last "
                    self.label = val

                elif "-" in val and len(val) >= 8:
                    pass  # date value (YYYY-MM-DD or YYYY-MM), already parsed as self.date

                else:
                    print("UNSUPPORTED assoc.value "+val)
                    
        
            
        pass

    # ratio spent of the day working on task ; 0.5 is half day
    def getTimeSpent(self):
        return self.len

    def getProject(self):
        from packages.database.database import Database
        return Database.instance.getProject(self.key)
    
    def getValue(self, uid):
        if not self.hasValues():
            return None
        
        for v in self.values:
            if uid in v:
                return v
        
        # NOT FOUND

        return None
    
    def hasRedirectedDate(self):
        return self.redirect != None

    # output DATETIME
    def getRedirectedDate(self):
        if self.redirect == None:
            return self.date
        else:
            return self.redirect

    # datetime YYYY
    def isYear(self, dateY):
        dt = self.getRedirectedDate()
        return str(dateY.year) == str(dt.year)
    
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
        output = "project:"+self.key
        output += "    date:"+str(self.date)
        if self.hasRedirectedDate(): output += " (redirect?"+str(self.getRedirectedDate())+")"
        output += "     len:"+str(self.len)
        return output

    def log(self, msg):

        if not self.verbose:
            return
        
        print(self.key+" ? "+msg)
    