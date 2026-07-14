from modules.system import *

"""
New format (preferred):
    DD: project
    DD: project 0.5

Legacy format (still supported):
    project:DD
    project:DD,0.5
"""

class Task:

    verbose = False

    key = None      # project uid

    def __init__(self, assoc, month_ctx=None):

        self.len = 1

        if assoc.key.strip().isdigit():
            self._parse_new(assoc, month_ctx)
        else:
            self._parse_legacy(assoc, month_ctx)

    # DD: project [duration|redirect]
    def _parse_new(self, assoc, month_ctx):

        day = assoc.key.strip()
        if month_ctx:
            dt = f"{month_ctx}-{int(day):02d}"
        else:
            dt = day
        self.date = strToYmd(dt)

        raw = assoc.value.strip()
        if "#" in raw:
            raw = raw[:raw.index("#")].strip()
        parts = raw.split()
        if not parts:
            self.key = None
            return
        self.key = parts[0]  # project uid

        for token in parts[1:]:
            self._parse_modifier(token)

    # project:DD[,modifiers]
    def _parse_legacy(self, assoc, month_ctx):

        self.key = assoc.key

        dt = assoc.values[0] if assoc.hasValues() else ""
        if month_ctx and dt.isdigit():
            dt = f"{month_ctx}-{int(dt):02d}"
        self.date = strToYmd(dt)

        if assoc.hasValues():
            for val in assoc.values[1:]:
                self._parse_modifier(val)

    def _parse_modifier(self, val):

        val = val.strip()

        if val == "0" or val == "0.0":
            self.len = 0

        elif "." in val:
            try:
                self.len = float(val)
            except ValueError:
                print("UNSUPPORTED modifier: " + val)

        elif "/" in val:
            sides = val.split("/")
            try:
                a, b = int(sides[0]), int(sides[1])
                self.len = 0 if b == 0 else a / b
            except ValueError:
                print("UNSUPPORTED modifier: " + val)

        else:
            print("UNSUPPORTED modifier: " + val)

    @property
    def is_off(self):
        return self.key == "off"

    @property
    def is_chome(self):
        return self.key == "chome"

    def getTimeSpent(self):
        """Return fraction of a day worked (0.5 = half day, 1 = full day)."""
        return self.len

    def isYear(self, dateY):
        """True if this task falls in the given year datetime."""
        return str(dateY.year) == str(self.date.year)

    def isMonth(self, dateYm):
        """True if this task falls in the given month datetime."""
        return dateYm.year == self.date.year and dateYm.month == self.date.month

    def isDate(self, dateYmd):
        """True if this task falls on the given date datetime."""
        return dateYmd.year == self.date.year and dateYmd.month == self.date.month and dateYmd.day == self.date.day

    def isDateRange(self, start, end):
        """True if this task's date falls within [start, end] datetimes inclusive."""
        self.log(str(self.date)+" VS ["+str(start)+","+str(end)+"]")
        if self.date < start:
            self.log("<<")
            return False
        if self.date > end:
            self.log(">>")
            return False
        self.log("ok")
        return True

    def stringify(self):
        return f"project:{self.key}    date:{self.date}    len:{self.len}"

    def log(self, msg):
        if not self.verbose:
            return
        print(self.key+" ? "+msg)
