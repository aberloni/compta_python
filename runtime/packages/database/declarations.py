"""
Declarations actually filed, read from database/ -- one line per declared
period, the value being the HT (chiffre d'affaires) declared:

    YYYY-N=HT

- tva/{YYYY}.tva       N = month (1-12, may be zero-padded): monthly TVA
                       declaration, e.g. `2026-1=3880` = January 2026.
- urssaf/{YYYY}.urssaf N = quarter (1-4): quarterly URSSAF declaration
                       (cotisations + CFP + versement libératoire), e.g.
                       `2026-1=8000` = T1 2026 (janv-mars).

0 = "déclaration néant" (nothing received that period, still declared).
Lines starting with # are comments. A period written twice: the last line
wins.
"""

from modules.path import Path
from packages.database.database import DatabaseType


class PeriodDeclarations:
    """HT declared per period, from every file of one database folder.
    Subclasses set db_type, max_n (12 months / 4 quarters) and key()."""

    db_type = None
    max_n = None

    def __init__(self):
        self.ht_by_period = {}  # key(year, n) -> HT declared
        self._load()

    def key(self, year, n):
        raise NotImplementedError

    def _load(self):
        label = self.db_type.name
        for f in sorted(Path.getAllFilesFromDbType(self.db_type)):
            for line in open(f, encoding="utf-8").read().splitlines():
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                period, sep, value = line.partition("=")
                try:
                    if not sep:
                        raise ValueError("'=' manquant")
                    year, dash, n = period.strip().partition("-")
                    year, n = int(year), int(n)
                    if not dash or not 1 <= n <= self.max_n:
                        raise ValueError(f"période invalide : {period.strip()}")
                    ht = float(value.strip().replace(",", "."))
                except ValueError as e:
                    print(f"{label}: skipping malformed line: {line!r} ({e})")
                    continue
                key = self.key(year, n)
                if key in self.ht_by_period:
                    print(f"{label}: {key} declared twice, keeping the last line: {line!r}")
                self.ht_by_period[key] = ht

    def status(self, key, computed_ht, current_key, tolerance=1.0):
        """(css class, label) for one period of a view's table: declared and
        matching the HT computed from payments received (within tolerance,
        declared amounts may be rounded), declared with a gap, current period,
        or still to declare (past periods must be declared even when nothing
        was received: "néant")."""
        if key in self.ht_by_period:
            gap = self.ht_by_period[key] - computed_ht
            if abs(gap) < tolerance:
                return "decl-ok", "✓ déclaré"
            return "decl-gap", "⚠ écart " + f"{gap:+,.2f} €".replace(",", " ")
        if key >= current_key:
            return "decl-none", "en cours"
        if computed_ht > 0:
            return "decl-due", "à déclarer"
        return "decl-due", "à déclarer (néant)"


class TvaDeclarations(PeriodDeclarations):
    """Monthly TVA declarations, keyed 'YYYY-MM' (as in view_tva.py)."""
    db_type = DatabaseType.tva
    max_n = 12

    def key(self, year, n):
        return f"{year:04d}-{n:02d}"


class UrssafDeclarations(PeriodDeclarations):
    """Quarterly URSSAF declarations, keyed 'YYYY-Tn' (as in view_trimester.py)."""
    db_type = DatabaseType.urssaf
    max_n = 4

    def key(self, year, n):
        return f"{year}-T{n}"
