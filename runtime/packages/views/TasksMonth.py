from datetime import datetime, date, timedelta

class TasksMonth:

    def __init__(self, y, m, tasks):
        self.year = y
        self.month = m
        
        self.cntWorkDays = None
        self.cntWorkedDays = None

        strDate = str(y)+"-"+str(m)
        print(strDate)

        self.date = datetime.strptime(strDate, "%Y-%m")

        self.tasks = []

        for t in tasks:
            if t.isMonth(self.date):
                self.tasks.append(t)


    """
        days not worked and not OFF
    """
    def countMissingDays(self):
        return self.countWorkedDays() - self.countWorkDays()


    """
        total of worked days during this month
    """
    def countWorkedDays(self):
        if self.cntWorkedDays != None:
            return self.cntWorkedDays
        
        cnt = 0
        for t in self.tasks:
            cnt += t.len
        return cnt

    """
        normal worked days in this month
    """
    def countWorkDays(self):
        if self.cntWorkDays != None:
            return self.cntWorkDays
        
        start = date(self.year, self.month, 1)
        end = date(self.year, self.month+1, 1)

        # get list of all days
        all_days = (start + timedelta(x + 1) for x in range((end - start).days))

        # filter business days
        # weekday from 0 to 4. 0 is monday adn 4 is friday
        # increase counter in each iteration if it is a weekday
        count = sum(1 for day in all_days if day.weekday() < 5)
        return count

    def stringify(self):
        output = str(self.date)
        output += "     x "+str(len(self.tasks))
        output += "     work : "+str(self.countWorkedDays()) +" / "+str(self.countWorkDays())
        output += "     miss : "+str(self.countMissingDays())
        return output
