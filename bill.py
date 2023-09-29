
from datetime import datetime

class Bill:
    
    verbose = False

    def __init__(self, project, data):
        
        # [UID=>START,END]
        self.project = project

        data = data[1:-1] # remove []

        _split = data.split("=>")
        self.uid = _split[0] # 2023-09-XX

        _dtSplit = _split[1]
        _dtSplit = _dtSplit.split(",")

        # real datetime, not strings
        self.start = datetime.strptime(_dtSplit[0], "%Y-%m-%d")
        self.end = datetime.strptime(_dtSplit[1], "%Y-%m-%d")

        self.tasks = []
        for t in project.tasks:
            if t.date >= self.start and t.date <= self.end:
                self.tasks.append(t)

        if self.verbose:
            print("bill#"+self.uid+", init = tasks x ", len(self.tasks))

    def compareBill(self, otherBill):
        if self.uid != otherBill.uid:
            return False
        
        if self.project.uid != otherBill.project.uid:
            return False
        
        return True
    
    def isSameWeek(self, dt):
        # input = datetime.strftime(str(y)+"-"+str(m), "%Y-%m")
        # print(self.uid)
        _dt = datetime.strptime(self.uid, "%Y-%m-%d")
        _week = _dt.strftime("%W")

        week = dt.strftime("%W")
        return _week == week
        
    def stringify(self):
        
        _start = self.start.strftime("%Y-%m-%d")
        _end  = self.end.strftime("%Y-%m-%d")

        return self.id+"=>"+_start+","+_end
    
    def getLabelDate(self):
        import calendar
        
        sMonth = calendar.month_abbr[int(self.start.strftime("%m"))]
        sMonth += " "+self.start.strftime("%Y")

        eMonth = calendar.month_abbr[int(self.end.strftime("%m"))]
        eMonth += " "+self.end.strftime("%Y")

        return sMonth+" | "+eMonth
    
    def countDays(self, Ym = None):

        output = 0
        for t in self.tasks:
            
            if Ym != None:
                if not t.isMonth(Ym):
                    continue

            output += t.len
        return output
    
    def getHT(self, Ym = None):
        return self.countDays(Ym) * self.project.getTaux()

    def getTVA(self):
        return float(self.project.assoc.filterKey("tva"))
    
    def getTvaTotal(self):
        return self.getTVA() * self.getHT()

    def getTTC(self):
        return self.getHT() + self.getTvaTotal()
    
    def dump(self):
        output = self.project.name

        output += "\n\nuid : "+self.uid

        output += "\n\nproject tasks x"+str(len(self.project.tasks))

        output += "\n\nbill tasks x"+str(len(self.tasks))
        for t in self.tasks:    
            output += "\n  "+t.stringify()
        
        output += "\n\nMontant:"
        output += "\n  HT : "+str(self.getHT())
        output += "\n  TTC : "+str(self.getTTC())

        return output
    
    def getBillFullUid(self):
        
        from database import Database

        dt = datetime.strptime(self.uid, "%Y-%m-%d")
        bills = Database.instance.getWeekBills(dt)

        inc = -1
        
        for i in range(0,len(bills)):
            
            print("#"+str(i)+" ? "+bills[i].uid+" vs "+self.uid)

            if bills[i].compareBill(self):
                inc = i

        if self.verbose:
            print(str(dt.year)+"-"+str(dt.month)+" => found TOTAL bills x", len(bills))
            print("searching for local bill : "+self.uid)
            print("index #"+str(inc))

        if inc < 0:
            return None

        # must inc because first is index 0
        inc += 1

        if inc < 10:
            inc = "0"+str(inc)
        else:
            inc = str(inc)
        
        week = dt.strftime("%W")

        # to Y-m
        trunc = self.uid.split("-")
        trunc = trunc[0]+"-"+trunc[1]
        return trunc + "_s"+week+"-"+inc

    def getTimespanMonths(self):

        cy = int(self.start.strftime("%Y"))
        ey = int(self.end.strftime("%Y"))
        cm = int(self.start.strftime("%m"))
        em = int(self.end.strftime("%m"))

        # print("starts @ "+str(cy)+"-"+str(cm))

        months = []

        safe = 999
        while cy <= ey and safe > 0:
            maxMonth = 12
            
            if cy == ey:
                maxMonth = em
            
            while cm <= maxMonth:
                output = str(cy)+"-"+str(cm)
                months.append(output)
                cm += 1
                safe -= 1
            
            cy += 1
            cm = 1

            safe -= 1

        if safe <= 0:
            print("error:safe")
        
        return months
    
    