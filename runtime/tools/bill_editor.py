"""
Write access to database/bills/{projectUid}.bill files -- used by the
"Éditer les factures" page's per-row save and "add bill" form (see
app_gui.py: update_bill_range() / add_bill()).

Bill blocks are a header line (date:start,end) optionally followed by
indented meta lines (label, designation, frais...) belonging to that bill,
usually separated from the next block by a blank line. Blank lines and
indentation are purely cosmetic -- Assoc.solveEntries() strips them -- so
the functions below only ever touch a single header line in place, or
append a brand new header line, never reflow the rest of the file.
"""

import os

from datetime import datetime

from modules.path import Path
from packages.database.database import DatabaseType
from modules.system import parseFlexibleDate


def bill_file_path(project_uid):
    return os.path.join(Path.getDbTypePath(DatabaseType.bills), f"{project_uid}.bill")


def _read_lines(path):
    if not os.path.isfile(path):
        return []
    with open(path, "r", encoding="utf-8") as f:
        return f.read().splitlines()


def _write_lines(path, lines):
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n" if lines else "")


def _is_header_line(stripped):
    """True if a stripped line is a bill block header ('YYYY-MM-DD: ...')."""
    key, sep, _ = stripped.partition(":")
    if not sep:
        return False
    try:
        datetime.strptime(key.strip(), "%Y-%m-%d")
        return True
    except ValueError:
        return False


def _validate_range(start, end):
    """Raise ValueError (French message) if start/end aren't parseable, or start is after end."""
    try:
        dt_start = parseFlexibleDate(start, use_first_day=True)
    except ValueError:
        raise ValueError(f"date de début invalide : {start!r}")
    try:
        dt_end = parseFlexibleDate(end)
    except ValueError:
        raise ValueError(f"date de fin invalide : {end!r}")
    if dt_start > dt_end:
        raise ValueError("la date de début doit précéder la date de fin")


def update_bill_range(project_uid, bill_uid, new_start, new_end):
    """Rewrite one bill header's start/end in place, keeping any '|forfait'
    suffix and every other line untouched."""
    path = bill_file_path(project_uid)
    if not os.path.isfile(path):
        return {"ok": False, "error": "fichier de factures introuvable"}

    try:
        _validate_range(new_start, new_end)
    except ValueError as e:
        return {"ok": False, "error": str(e)}

    lines = _read_lines(path)
    for idx, line in enumerate(lines):
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        key, sep, value = stripped.partition(":")
        if sep and key.strip() == bill_uid:
            forfait_suffix = ""
            if "|" in value:
                forfait_suffix = "|" + value.split("|", 1)[1].strip()
            lines[idx] = f"{bill_uid}: {new_start}, {new_end}{forfait_suffix}"
            _write_lines(path, lines)
            return {"ok": True}

    return {"ok": False, "error": f"facture {bill_uid} introuvable pour ce projet"}


def add_bill(project_uid, bill_uid, start, end):
    """Append a new bill header line for project_uid. Fails if a bill with
    the same date already exists for that project."""
    try:
        datetime.strptime(bill_uid or "", "%Y-%m-%d")
    except ValueError:
        return {"ok": False, "error": "la date de facture doit être au format AAAA-MM-JJ"}

    try:
        _validate_range(start, end)
    except ValueError as e:
        return {"ok": False, "error": str(e)}

    path = bill_file_path(project_uid)
    lines = _read_lines(path)

    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        key, sep, _ = stripped.partition(":")
        if sep and key.strip() == bill_uid:
            return {"ok": False, "error": f"une facture existe déjà le {bill_uid} pour ce projet"}

    if lines and lines[-1].strip() != "":
        lines.append("")
    lines.append(f"{bill_uid}: {start}, {end}")

    os.makedirs(os.path.dirname(path), exist_ok=True)
    _write_lines(path, lines)
    return {"ok": True}


def delete_bill(project_uid, bill_uid):
    """Remove one bill block (header line + its meta lines, up to the next
    header or EOF) from database/bills/{project_uid}.bill. Refuses if any
    received wire transfer is already linked to this bill's full UID."""
    from packages.database.database import Database
    from packages.database.wiring import Wiring

    db = Database.init_billing()
    project = db.getProject(project_uid)
    bill = next((b for b in project.bills if b.uid == bill_uid), None) if project else None
    if bill is None:
        return {"ok": False, "error": f"facture {bill_uid} introuvable pour ce projet"}

    fuid = bill.getFullUid() or bill.uid
    linked = [w for w in Wiring().wires if w.bill_fuid == fuid]
    if linked:
        return {"ok": False, "error": f"{len(linked)} virement(s) déjà associé(s) à cette facture -- suppression impossible"}

    path = bill_file_path(project_uid)
    lines = _read_lines(path)

    start_idx = None
    for idx, line in enumerate(lines):
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        key, sep, _ = stripped.partition(":")
        if sep and key.strip() == bill_uid:
            start_idx = idx
            break

    if start_idx is None:
        return {"ok": False, "error": f"facture {bill_uid} introuvable dans le fichier"}

    end_idx = len(lines)
    for idx in range(start_idx + 1, len(lines)):
        stripped = lines[idx].strip()
        if stripped and _is_header_line(stripped):
            end_idx = idx
            break

    del lines[start_idx:end_idx]
    _write_lines(path, lines)
    return {"ok": True}
