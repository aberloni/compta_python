"""
Write access to database/wiring/{year}.wire files -- used by the "Virements"
page's "add wire" form and per-row "associate to a bill" control (see
app_gui.py: add_wire() / associate_wire()).

Wire files are one line per virement, whitespace-separated:
    CLIENT_UID  YYYY-MM-DD  AMOUNT  [BILL_FUID]
associate_wire() rewrites a single line in place, targeting it by
(source file, line number) as recorded on the Wire object when the file was
loaded (see packages/database/wiring.py) -- never by content-matching, so it
stays correct even with duplicate-looking wires.
"""

import os

from datetime import datetime

from modules.path import Path
from packages.database.database import Database, DatabaseType


def wire_file_path(year):
    return os.path.join(Path.getDbTypePath(DatabaseType.wiring), f"{year}.wire")


def _read_lines(path):
    if not os.path.isfile(path):
        return []
    with open(path, "r", encoding="utf-8") as f:
        return f.read().splitlines()


def _write_lines(path, lines):
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n" if lines else "")


def _find_bill_fuid(bill_fuid):
    """Return True if bill_fuid matches an existing bill somewhere in the database."""
    db = Database.init_billing()
    for p in db.projects:
        for b in p.bills:
            if (b.getFullUid() or b.uid) == bill_fuid:
                return True
    return False


def add_wire(client_uid, date_str, amount, bill_fuid=None):
    """Append a new wire line to database/wiring/{year}.wire, year taken from date_str."""
    client_uid = (client_uid or "").strip()
    if not client_uid:
        return {"ok": False, "error": "le client est requis"}

    date_str = (date_str or "").strip()
    try:
        dt = datetime.strptime(date_str, "%Y-%m-%d")
    except ValueError:
        return {"ok": False, "error": f"date invalide (attendu AAAA-MM-JJ) : {date_str!r}"}

    amount = (amount or "").strip()
    try:
        float(amount)
    except ValueError:
        return {"ok": False, "error": f"montant invalide : {amount!r}"}

    bill_fuid = (bill_fuid or "").strip() or None
    if bill_fuid and not _find_bill_fuid(bill_fuid):
        return {"ok": False, "error": f"facture {bill_fuid!r} introuvable"}

    path = wire_file_path(dt.year)
    lines = _read_lines(path)
    if lines and lines[-1].strip() != "":
        lines.append("")

    line = f"{client_uid}\t{date_str}\t{amount}"
    if bill_fuid:
        line += f"\t{bill_fuid}"
    lines.append(line)

    os.makedirs(os.path.dirname(path), exist_ok=True)
    _write_lines(path, lines)
    return {"ok": True}


def associate_wire(filename, line_no, bill_fuid):
    """Set (or clear, if bill_fuid is empty) the bill association on one wire
    line, identified by its filename (under database/wiring/) + line number."""
    filename = os.path.basename((filename or "").strip())
    source_file = os.path.join(Path.getDbTypePath(DatabaseType.wiring), filename) if filename else ""
    if not filename or not os.path.isfile(source_file):
        return {"ok": False, "error": "fichier de virements introuvable"}

    bill_fuid = (bill_fuid or "").strip() or None
    if bill_fuid and not _find_bill_fuid(bill_fuid):
        return {"ok": False, "error": f"facture {bill_fuid!r} introuvable"}

    lines = _read_lines(source_file)
    try:
        line_no = int(line_no)
    except (TypeError, ValueError):
        return {"ok": False, "error": "ligne de virement introuvable"}
    if line_no < 0 or line_no >= len(lines):
        return {"ok": False, "error": "ligne de virement introuvable"}

    parts = lines[line_no].split()
    if len(parts) < 3:
        return {"ok": False, "error": "ligne de virement introuvable"}

    new_line = f"{parts[0]}\t{parts[1]}\t{parts[2]}"
    if bill_fuid:
        new_line += f"\t{bill_fuid}"
    lines[line_no] = new_line

    _write_lines(source_file, lines)
    return {"ok": True}
