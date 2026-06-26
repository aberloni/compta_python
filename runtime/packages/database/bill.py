from datetime import datetime
from datetime import timedelta
import calendar

from modules.system import *


def _iter_months(start, end):
    """Yield (year, month) tuples from start to end datetimes inclusive."""
    cy, cm = start.year, start.month
    ey, em = end.year, end.month
    while (cy, cm) <= (ey, em):
        yield (cy, cm)
        cm += 1
        if cm > 12:
            cm = 1
            cy += 1


class Bill:

    verbose = False

    uid = None      # invoice date YYYY-MM-DD
    project = None
    fullUID = None  # generated: {YYYY-MM}_s{week}-{idx}

    label = ""       # replaces "Prestation x N j" in line items
    designation = "" # subtitle above the line items table

    start = None
    end = None
    tasks = None
    limit = None    # payment deadline (uid + 30 days)

    def __init__(self, project, uid, billHeader):
        self.project = project
        self.uid = uid

        self.limit = datetime.strptime(self.uid, "%Y-%m-%d")
        self.limit = (self.limit + timedelta(days=30)).strftime("%Y-%m-%d")

        self.forfait = None   # fixed HT amount (skips days × taux)
        self.jours = None     # total day count override (display + HT when no forfait)
        self.transactions = []

        self.injectData(billHeader)

    def addTransaction(self, key, value):
        """Append a BillTransaction (frais) to this bill."""
        bt = BillTransaction(key, value)
        self.transactions.append(bt)
        if self.verbose: print("+Frais :  bill:"+self.uid+" --> x"+str(len(self.transactions)))

    def injectData(self, data):
        """Parse the bill header line: 'start, end' with optional legacy '|jours'."""
        # legacy: |N was day count override → now stored as jours
        if "|" in data:
            splitted = data.split("|")
            data = splitted[0]
            self.jours = float(splitted[1])

        _dtSplit = data.split(",")

        self.log("    bill.range : "+_dtSplit[0]+" -> "+_dtSplit[1])

        self.start = datetime.strptime(_dtSplit[0].strip(), "%Y-%m-%d")

        try:
            self.end = datetime.strptime(_dtSplit[1].strip(), "%Y-%m-%d")
        except ValueError:
            print("ERROR : invalid date : ", _dtSplit[1])

        self.tasks = [t for t in self.project.tasks if t.isDateRange(self.start, self.end)]

        self.log("    bill.tasks x "+str(len(self.tasks))+" / total in project x "+str(len(self.project.tasks)))

    def getClient(self):
        """Return the client applicable at the start of this bill's period."""
        return self.project.getClient(self.start)

    def hasTransactions(self):
        """True if this bill has extra frais lines."""
        return len(self.transactions) > 0

    def compareBill(self, otherBill):
        """True if both bills share the same uid and project uid."""
        return self.uid == otherBill.uid and self.project.uid == otherBill.project.uid

    def getDatetime(self):
        """Return bill date (uid) as datetime."""
        return datetime.strptime(self.uid, "%Y-%m-%d")

    def isYear(self, year):
        """True if the bill date falls in the given year (int)."""
        return int(self.getDatetime().strftime("%Y")) == int(year)

    def parse_date(self, s):
        """Parse a date string accepting YYYY-MM-DD, YYYY-MM (→ last day) or YYYY (→ Dec 31)."""
        FORMATS = ["%Y-%m-%d", "%Y-%m", "%Y"]
        for fmt in FORMATS:
            try:
                dt = datetime.strptime(s, fmt)
                if fmt == "%Y-%m":
                    last_day = calendar.monthrange(dt.year, dt.month)[1]
                    return datetime(dt.year, dt.month, last_day)
                if fmt == "%Y":
                    return datetime(dt.year, 12, 31)
                return dt
            except ValueError:
                continue
        raise ValueError(f"Date '{s}' does not match expected formats")

    def isDateRangeOverlap(self, range):
        """True if this bill's period overlaps with the given [start, end] string range."""
        if len(range) <= 0:
            print("error:need range")
            return

        start = self.parse_date(range[0])
        end = self.parse_date(range[1]) if len(range) > 1 else start

        print(str(self.start)+","+str(self.end)+" ? "+str(start)+","+str(end))

        return start <= self.end and self.start <= end

    def isTimeframe(self, start, end):
        """True if this bill's period is fully contained within [start, end] datetimes."""
        return self.start >= start and self.end <= end

    def isSameWeek(self, dt):
        """True if the bill date is in the same year+week as the given datetime."""
        _dt = self.getDatetime()
        return _dt.strftime("%Y") == dt.strftime("%Y") and _dt.strftime("%W") == dt.strftime("%W")

    def stringify(self):
        return f"{self.uid}=>{self.start:%Y-%m-%d},{self.end:%Y-%m-%d}"

    def isForfait(self):
        """True if this bill has a fixed HT amount (forfait keyword)."""
        return self.forfait is not None

    def getLabelDate(self):
        """Return a human-readable period label: 'Jan 2026 | Mar 2026'."""
        sMonth = calendar.month_abbr[int(self.start.strftime("%m"))] + " " + self.start.strftime("%Y")
        eMonth = calendar.month_abbr[int(self.end.strftime("%m"))] + " " + self.end.strftime("%Y")
        return sMonth + " | " + eMonth

    def countDays(self, Ym=None):
        """Return total days worked. If Ym ('YYYY-M'), filter to that month only.
        If jours is set and no month filter, returns the override total."""
        if self.jours is not None and Ym is None:
            return self.jours

        dYm = strToYmd(Ym) if Ym is not None else None

        output = 0
        for t in self.tasks:
            if dYm is not None and not t.isMonth(dYm):
                continue
            output += t.getTimeSpent()
        return output

    def getHT(self, Ym=None):
        """Return HT amount.
        - forfait: returns fixed amount directly.
        - jours (no Ym): jours × taux at bill start.
        - otherwise: sums each month's days × taux for that month."""
        if self.isForfait():
            return self.forfait

        if self.jours is not None and Ym is None:
            return self.jours * self.project.getTaux(self.start)

        if Ym is not None:
            parts = Ym.split("-")
            dt = datetime(int(parts[0]), int(parts[1]), 1)
            return self.countDays(Ym) * self.project.getTaux(dt)

        total = 0.0
        for yr, mo in _iter_months(self.start, self.end):
            m_str = f"{yr}-{mo}"
            dt = datetime(yr, mo, 1)
            total += self.countDays(m_str) * self.project.getTaux(dt)
        return total

    def getTVA(self):
        """Return TVA rate as a float (e.g. 0.2)."""
        return float(self.project.assoc.filterKey("tva"))

    def getTvaTotal(self):
        """Return TVA amount in €."""
        return self.getTVA() * self.getHT()

    def getTTC(self):
        """Return TTC amount including frais."""
        return self.getHT() + self.getTvaTotal() + self.getTransactionsTTC()

    def getTransactionsTTC(self):
        """Return total of all frais lines in €."""
        return round(sum(t.solvePrice() for t in self.transactions), 2)

    def dump(self):
        """Return a markdown summary of this bill (used for debug .dump files)."""
        output = self.project.name + "\n"
        output += f"\nuid         {self.uid}"
        output += f"\ndate range  [{self.start:%Y-%m-%d},{self.end:%Y-%m-%d}]"
        output += "\n\nproject total tasks x" + str(len(self.project.tasks))
        output += "\nthis bill tasks x" + str(len(self.tasks))
        for t in self.tasks:
            output += "\n  " + t.stringify()
        output += "\n\nMontant:"
        output += "\n  HT : " + str(self.getHT())
        output += "\n  TTC : " + str(self.getTTC())
        return output

    def solveFullUid(self):
        """Compute the full bill UID: {YYYY-MM}_s{week}-{idx} where idx is position among all bills that week."""
        from packages.database.database import Database

        dt = datetime.strptime(self.uid, "%Y-%m-%d")
        bills = Database.instance.getWeekBills(dt)
        week = dt.strftime("%W")

        if self.verbose:
            print("bill?fullUID    dt: "+str(dt)+" , week: "+str(week))
            print("total bills this week : "+str(len(bills)))

        idx = -1
        for i in range(0, len(bills)):
            if self.verbose: print("     #"+str(i)+" ? "+bills[i].uid+" @ "+bills[i].project.uid)
            if bills[i].compareBill(self):
                idx = i

        if idx < 0:
            print("bill?FUID    "+self.uid+" not found in all bills of week #"+str(week))
            return None

        idx += 1
        idx = ("0" + str(idx)) if idx < 10 else str(idx)

        trunc = self.uid[:7]  # YYYY-MM
        return trunc + "_s" + week + "-" + idx

    def getFullUid(self):
        """Return cached full UID, computing it on first call."""
        if self.fullUID is None:
            self.fullUID = self.solveFullUid()
        return self.fullUID

    def getTimespanMonths(self):
        """Return list of 'YYYY-M' strings for each month in the bill period."""
        months = []
        for yr, mo in _iter_months(self.start, self.end):
            months.append(f"{yr}-{mo}")
        return months

    def log(self, msg):
        if not Bill.verbose:
            return
        print("bill#" + self.uid + " : " + msg)


class BillTransaction:
    """An additional line item on a bill (frais: label, unit_price, qty)."""

    def __init__(self, type, value):
        split = value.split(",")
        self.type = type
        self.label = split[0].strip()
        self.price = float(split[1]) if len(split) > 1 else 0
        self.quantity = float(split[2]) if len(split) > 2 else 1

    def solvePrice(self):
        """Return total price (price × qty, rounded to 2 decimals)."""
        return self.price if self.quantity <= 1 else round(self.price * self.quantity, 2)

    def getType(self):
        return self.type
