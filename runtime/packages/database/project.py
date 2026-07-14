
from packages.database.database import Database, DatabaseType
from packages.database.bill import BillTransaction

from modules.assocs import Assoc
from modules.system import parseFlexibleDate

from datetime import datetime


def _parse_dated_entries(entries):
    """
    Generic parser for dated key entries.
    Returns (base_value: str|None, dated: list[(datetime, str)])

    Formats accepted:
        key:uid                    → base value (no date)
        key:2025-06-01=newuid      → value effective from that date
    """
    base = None
    dated = []
    for e in entries:
        v = e.value
        if "=" in v:
            parts = v.split("=", 1)
            dt = parseFlexibleDate(parts[0].strip(), use_first_day=True)
            dated.append((dt, parts[1].strip()))
        else:
            base = v
    dated.sort(key=lambda x: x[0])
    return base, dated


def _resolve_at_date(base, dated, date):
    """Return the value applicable at `date` from (base, dated) pairs."""
    result = base
    for dt, val in dated:
        if date is None or dt <= date:
            result = val
    return result


def _parse_taux_entries(entries):
    """
    Parse all 'taux' AssocEntry values.
    Returns (base: int|None, dated: list[(datetime, int)])

    Formats accepted:
        taux:280               → base rate (no date)
        taux:2024-06-01=320    → rate effective from that date
    """
    base = None
    dated = []
    for e in entries:
        v = e.value
        if "=" in v:
            parts = v.split("=", 1)
            dt = parseFlexibleDate(parts[0].strip(), use_first_day=True)
            dated.append((dt, int(parts[1].strip())))
        else:
            base = int(v)
    dated.sort(key=lambda x: x[0])
    return base, dated

class Project:

    verbose = False
    
    uid = None
    name = None
    
    client = None
    bills = None # array
    
    def __init__(self, fileName):
        
        self.assoc = Assoc(fileName, DatabaseType.projects)

        self.uid = self.assoc.filterKey("uid")
        self.name = self.assoc.filterKey("name")

        # client history parsed lazily via getClient(date)
        # self.client kept as shortcut for the base (no-date) client — rétrocompat
        _client_entries = self.assoc.filterKeys("client")
        _base_uid, self._client_dated = _parse_dated_entries(_client_entries)
        self.client = Database.instance.getClient(_base_uid)

        pass
    
    def dump(self):
        """Print a debug summary of this project's tasks and bills."""
        print("=== dump ===")
        print(self.uid, " tasks[] ", len(self.tasks))
        
        for t in self.tasks:
            print(t.stringify())

        for b in self.bills:
            print(b.stringify())
        
        print("======")
        pass
    
    def assignTasks(self, tasks):
        """Filter and attach tasks belonging to this project, then generate bills."""
        self.tasks = []
        for t in tasks:
            if t.key == self.uid:
                self.tasks.append(t)
        
        if self.verbose:
            print("project "+self.uid+" was assigned tasks x", len(self.tasks))

        # tasks are ready : solve project bill data
        self.generateBills()

        pass

    def generateBills(self):
        """Parse the project's .bill file and populate self.bills."""
        from modules.assocs import Assoc
        from packages.database.database import DatabaseType
        from packages.database.bill import Bill

        # init
        path = self.uid
        self.bills = []
        
        # any bill file matching this project ?
        if not Assoc.has(path, DatabaseType.bills):
            print("project @"+self.uid+" has no bills file")
            return
        
        # search for bills linked to this project
        assocs = Assoc(path, DatabaseType.bills)

        bill = None
        for e in assocs.entries: # each key:value lines

            #print("project.assoc :  "+e.key+" = "+e.value)

            # each line is either a bill header
            # or some detail for that bill
            
            #{YYYY-mm-dd} OR {type}
            type = e.key[0] # first symbol of line

            if type.isnumeric(): # starts with a number = new bill
                
                bill = Bill(self, e.key, e.value)
                
                if self.verbose: print("+Bill : "+e.key)
                
                self.bills.append(bill)
                
            else: # lines between each bill header
                
                # additionnal fields for this bill
                
                overrideKey = e.key.lower()

                match overrideKey:
                    case "frais":
                        bill.addTransaction(overrideKey, e.value)
                        if self.verbose: print("+Frais :     "+overrideKey+"="+e.value)

                    case "forfait":
                        bill.forfait = float(e.value)
                        if self.verbose: print("+Forfait :   "+e.value)

                    case "jours":
                        bill.jours = float(e.value)
                        if self.verbose: print("+Jours :     "+e.value)

                    case "label":
                        bill.label = e.value
                        if self.verbose: print("+Label :     "+bill.label)

                    case "designation":
                        bill.designation = e.value
                        if self.verbose: print("+Designation :   "+bill.designation)

                    case "objet":
                        self.name = e.value
                        if self.verbose: print("+Objet :   "+self.name)
                        
        #print("bill : "+self.uid+" , solved x" ,len(self.bills))
                
        
    def getBills(self, rangeDate = None):
        """Return bills overlapping rangeDate ['YYYY-MM', 'YYYY-MM'], or all bills if None."""
        if rangeDate == None:
            return self.bills
        
        ret = []
        
        print(":before x"+str(len(self.bills)))

        for b in self.bills:
            inRange = b.isDateRangeOverlap(rangeDate)
            
            print(str(b.uid)+" ? "+str(rangeDate)+" "+str(inRange))

            if inRange :
                ret.append(b)
        
        print(":after x"+str(len(ret)))

        return ret

    def getBillsInDateRange(self, start, end):
        """Return bills whose period is fully contained within [start, end] datetimes."""
        _bills = []
        for b in self.bills:
            if b.isTimeframe(start, end):
                _bills.append(b)
                
        return _bills

    def getMatchingWeekBill(self, dateStr):
        """Return the first bill of this project in the same week as dateStr ('YYYY-MM-DD')."""
        date = datetime.strptime(dateStr, "%Y-%m-%d")

        for b in self.bills:
            if b.isSameWeek(date):
                return b
        
        print("NOT FOUND : bill:"+dateStr)
        
        return None

    def getMatchingWeekBills(self, date):
        """Return all bills of this project in the same week as `date` datetime."""
        output = []

        #week = datetime.strptime(date, "%Y-%m-%d")
        #week = week.strftime("%W")

        for b in self.bills:
            if b.isSameWeek(date):
                output.append(b)
        
        if self.verbose and len(output) > 0:
            print("matching.week    project:"+self.uid+" @"+str(date)+" , found project bills x"+str(len(output)))

        return output 
    
    def getClient(self, date=None):
        """
        Return the Client applicable at `date`.
        If date is None, returns the base client.

        File formats:
            client:darjeeling              → base client (rétrocompat)
            client:2025-06-01=nouveauclient → client effective from that date
        """
        if not self._client_dated:
            return self.client  # simple case, rétrocompat

        uid = _resolve_at_date(
            self.client.uid if self.client else None,
            self._client_dated,
            date
        )
        return Database.instance.getClient(uid)

    def getTaux(self, date=None):
        """
        Return the daily rate (taux) applicable at `date`.
        If date is None, returns the base rate (or the latest dated one).

        File formats:
            taux:280               → base rate, always applicable
            taux:2024-06-01=320    → rate effective from 2024-06-01

        Multiple taux lines can coexist. The most recent one <= date wins.
        """
        entries = self.assoc.filterKeys("taux")
        base, dated = _parse_taux_entries(entries)

        if not dated:
            return base  # simple case, rétrocompat

        if date is None:
            # no date given: use last dated rate, fallback to base
            return dated[-1][1] if dated else base

        result = base
        for dt, t in dated:
            if dt <= date:
                result = t
        return result

    def getTauxRange(self, start, end):
        """
        Return sorted list of unique taux applied between start and end datetimes.
        Used for display ("280 → 320 € HT").
        """
        entries = self.assoc.filterKeys("taux")
        base, dated = _parse_taux_entries(entries)

        from packages.database.bill import _iter_months
        seen = []
        for m in _iter_months(start, end):
            dt = datetime(m[0], m[1], 1)
            t = base
            for d, rate in dated:
                if d <= dt:
                    t = rate
            if t not in seen:
                seen.append(t)
        return seen
