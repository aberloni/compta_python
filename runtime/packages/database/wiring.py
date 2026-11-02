"""
Loads all .wire files and exposes received amounts per client.

Wire file format (one line per virement):
    CLIENT_UID<TAB>YYYY-MM-DD<TAB>AMOUNT_TTC[<TAB>BILL_FUID[,BILL_FUID...]]
Fields are tab-separated (any whitespace is accepted when reading).
One virement may pay several bills: list their full UIDs, comma-separated.
Its amount is then split across them in the listed order (see
Wiring.payments_by_fuid()).
"""

from collections import defaultdict
from datetime import datetime
from modules.path import Path
from packages.database.database import DatabaseType
import os


def parse_bill_fuids(text):
    """Split a 'fuid1,fuid2' field into a list of full UIDs (empty items dropped)."""
    return [f.strip() for f in (text or "").split(",") if f.strip()]


class Wire:
    """One received bank transfer."""

    def __init__(self, client_uid, date_str, amount, bill_fuids=None, source_file=None, line_no=None):
        self.client_uid = client_uid.strip().lower()
        self.date = datetime.strptime(date_str.strip(), "%Y-%m-%d")
        self.amount = float(amount.strip())
        self.bill_fuids = parse_bill_fuids(bill_fuids)
        # location of the line this wire was parsed from -- lets an editor
        # rewrite that exact line without guessing which one matched
        self.source_file = source_file
        self.line_no = line_no


class Payment:
    """The share of one wire allocated to one bill."""

    def __init__(self, wire, fuid, amount):
        self.wire = wire
        self.fuid = fuid
        self.amount = amount
        self.date = wire.date


class Wiring:
    """All wires loaded from wiring/ folder."""

    def __init__(self):
        self.wires = []
        self._load()

    def _load(self):
        files = Path.getAllFilesFromDbType(DatabaseType.wiring)
        for f in files:
            lines = open(f, encoding="utf-8").read().splitlines()
            for line_no, line in enumerate(lines):
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                parts = line.split()
                if len(parts) < 3:
                    print(f"wiring: skipping malformed line: {line!r}")
                    continue
                # "fuid1, fuid2" (spaces after commas) is split by split() -- glue it back
                bill_fuids = "".join(parts[3:]) if len(parts) >= 4 else None
                self.wires.append(Wire(parts[0], parts[1], parts[2], bill_fuids, source_file=f, line_no=line_no))

    def linked_fuids(self):
        """Return the set of bill full UIDs referenced by at least one wire."""
        return {fuid for w in self.wires for fuid in w.bill_fuids}

    def payments_by_fuid(self, db, client_uids=None):
        """Return {bill_fuid: [Payment]} -- what each bill received, and when.

        A wire listing one bill gives it its whole amount. A wire listing
        several bills is split in the listed order: each bill takes what it
        still owes (its TTC minus earlier payments), the last one takes
        whatever is left. Wires are processed by date, so a bill already
        partly paid by an earlier wire only takes its remaining due.
        client_uids, if given, keeps only wires from those clients.
        """
        ttc_by_fuid = {(b.getFullUid() or b.uid): b.getTTC() for p in db.projects for b in p.bills}
        paid = defaultdict(float)
        out = defaultdict(list)
        for w in sorted(self.wires, key=lambda x: x.date):
            if client_uids is not None and w.client_uid not in client_uids:
                continue
            left = w.amount
            for i, fuid in enumerate(w.bill_fuids):
                if i == len(w.bill_fuids) - 1:
                    share = left
                else:
                    due = max(0.0, ttc_by_fuid.get(fuid, left) - paid[fuid])
                    share = min(left, due)
                left -= share
                if share <= 0.005:
                    continue  # nothing left for it: this wire must not count as its payment date
                paid[fuid] += share
                out[fuid].append(Payment(w, fuid, share))
        return out

    def total_received(self, client_uid):
        """Return total TTC received for a given client uid."""
        return sum(w.amount for w in self.wires if w.client_uid == client_uid.lower())

    def by_client(self):
        """Return dict {client_uid: total_received}."""
        out = {}
        for w in self.wires:
            out[w.client_uid] = out.get(w.client_uid, 0.0) + w.amount
        return out
