"""
Loads all .wire files and exposes received amounts per client.

Wire file format (one line per virement):
    CLIENT_UID    YYYY-MM-DD    AMOUNT_TTC
Fields are whitespace-separated.
"""

from datetime import datetime
from modules.path import Path
from packages.database.database import DatabaseType
import os


class Wire:
    """One received bank transfer."""

    def __init__(self, client_uid, date_str, amount, bill_fuid=None):
        self.client_uid = client_uid.strip().lower()
        self.date = datetime.strptime(date_str.strip(), "%Y-%m-%d")
        self.amount = float(amount.strip())
        self.bill_fuid = bill_fuid.strip() if bill_fuid else None


class Wiring:
    """All wires loaded from wiring/ folder."""

    def __init__(self):
        self.wires = []
        self._load()

    def _load(self):
        files = Path.getAllFilesFromDbType(DatabaseType.wiring)
        for f in files:
            lines = open(f, encoding="utf-8").read().splitlines()
            for line in lines:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                parts = line.split()
                if len(parts) < 3:
                    print(f"wiring: skipping malformed line: {line!r}")
                    continue
                bill_fuid = parts[3] if len(parts) >= 4 else None
                self.wires.append(Wire(parts[0], parts[1], parts[2], bill_fuid))

    def total_received(self, client_uid):
        """Return total TTC received for a given client uid."""
        return sum(w.amount for w in self.wires if w.client_uid == client_uid.lower())

    def by_client(self):
        """Return dict {client_uid: total_received}."""
        out = {}
        for w in self.wires:
            out[w.client_uid] = out.get(w.client_uid, 0.0) + w.amount
        return out
