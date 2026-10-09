"""
Cotisations sociales, CFP et versement libératoire — taux applicables à
l'auto-entrepreneur, chargés depuis database/infos/impots.info.
Voir documentation/microe.md pour le détail des taux et leurs sources.
"""

from modules.assocs import Assoc
from modules.system import parseFlexibleDate
from packages.database.database import DatabaseType


def _parse_rate_entries(entries):
    """
    Parse dated rate entries (float values).
    Returns (base: float|None, dated: list[(datetime, float)]).

    Formats accepted:
        key:0.22               → base rate, always applicable
        key:2024-06-01=0.24    → rate effective from that date
    """
    base = None
    dated = []
    for e in entries:
        v = e.value
        if "=" in v:
            parts = v.split("=", 1)
            dt = parseFlexibleDate(parts[0].strip(), use_first_day=True)
            dated.append((dt, float(parts[1].strip())))
        else:
            base = float(v)
    dated.sort(key=lambda x: x[0])
    return base, dated


def _resolve_rate(base, dated, date):
    """Return the rate applicable at `date` from (base, dated) pairs, most recent <= date wins."""
    result = base
    for dt, rate in dated:
        if date is None or dt <= date:
            result = rate
    return result if result is not None else 0.0


class Impots:
    """Taux de cotisations sociales, CFP et versement libératoire, par date."""

    def __init__(self):
        self.assoc = Assoc("impots", DatabaseType.infos)

    def getCotisations(self, date=None):
        base, dated = _parse_rate_entries(self.assoc.filterKeys("cotisations"))
        return _resolve_rate(base, dated, date)

    def getCfp(self, date=None):
        base, dated = _parse_rate_entries(self.assoc.filterKeys("cfp"))
        return _resolve_rate(base, dated, date)

    def getLiberatoire(self, date=None):
        base, dated = _parse_rate_entries(self.assoc.filterKeys("liberatoire"))
        return _resolve_rate(base, dated, date)
