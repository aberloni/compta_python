"""
Write access to database/clients/{uid}.cli files -- used by the "Clients"
page's per-row save form and "add client" form (see app_gui.py:
update_client() / add_client()).

Client files are simple key:value lines (uid, name, address, creditor,
country, tva, color). update_client() rewrites/removes/appends individual
key lines in place, keeping every other line untouched. uid is never
rewritten here -- it's the filename itself, and projects/ and wiring/ files
reference it, so renaming would require updating every reference.

A client is never left without a color: an empty color field always gets a
color assigned instead (see _random_unused_color()), rather than clearing
the key.
"""

import os
import random
import re

from modules.path import Path
from packages.database.database import DatabaseType

EDITABLE_KEYS = ["name", "address", "creditor", "country", "tva", "color"]

# same categorical palette used elsewhere for auto-assigned colors (see
# view_billing.py's pie chart) -- picked from first, falling back to a
# random hex once every palette color is already taken by another client.
PALETTE = ["#4e79a7", "#f28e2b", "#e15759", "#76b7b2", "#59a14f",
           "#edc948", "#b07aa1", "#ff9da7", "#9c755f", "#bab0ac"]


def _used_colors(exclude_uid=None):
    """Hex colors already assigned to other clients, lowercased."""
    from packages.database.database import Database
    used = set()
    for c in Database.init_billing().clients:
        if c.color and c.uid != exclude_uid:
            used.add(c.color.strip().lower())
    return used


def _random_unused_color(exclude_uid=None):
    """A color no other client is already using."""
    used = _used_colors(exclude_uid)
    candidates = [c for c in PALETTE if c.lower() not in used]
    if candidates:
        return random.choice(candidates)
    for _ in range(50):
        color = "#{:06x}".format(random.randint(0, 0xFFFFFF))
        if color.lower() not in used:
            return color
    return "#{:06x}".format(random.randint(0, 0xFFFFFF))


def client_file_path(uid):
    return os.path.join(Path.getDbTypePath(DatabaseType.clients), f"{uid}.cli")


def _read_lines(path):
    if not os.path.isfile(path):
        return []
    with open(path, "r", encoding="utf-8") as f:
        return f.read().splitlines()


def _write_lines(path, lines):
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n" if lines else "")


def _set_key(lines, key, value):
    """Set (or remove, if value is empty) a 'key:value' line in place;
    append a new line at the end if the key isn't present yet."""
    value = (value or "").strip()
    for idx, line in enumerate(lines):
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        k, sep, _ = stripped.partition(":")
        if sep and k.strip() == key:
            if value:
                lines[idx] = f"{key}:{value}"
            else:
                del lines[idx]
            return
    if value:
        lines.append(f"{key}:{value}")


def update_client(uid, name, address, creditor="", country="", tva="", color=""):
    """Update an existing client's editable fields. name/address are
    required; creditor/country/tva/color are optional (blank clears them)."""
    path = client_file_path(uid)
    if not os.path.isfile(path):
        return {"ok": False, "error": "client introuvable"}

    name = (name or "").strip()
    if not name:
        return {"ok": False, "error": "le nom est requis"}

    address = (address or "").strip()
    if not address:
        return {"ok": False, "error": "l'adresse est requise"}

    color = (color or "").strip() or _random_unused_color(exclude_uid=uid)

    lines = _read_lines(path)
    _set_key(lines, "name", name)
    _set_key(lines, "address", address)
    _set_key(lines, "creditor", creditor)
    _set_key(lines, "country", country)
    _set_key(lines, "tva", tva)
    _set_key(lines, "color", color)

    _write_lines(path, lines)
    return {"ok": True}


def add_client(uid, name, address, creditor="", country="", tva="", color=""):
    """Create a new database/clients/{uid}.cli file. Fails if uid is empty,
    invalid, or a client with that uid already exists."""
    uid = (uid or "").strip()
    if not uid or not re.match(r"^[a-zA-Z0-9_-]+$", uid):
        return {"ok": False, "error": "identifiant invalide (lettres, chiffres, - et _ uniquement)"}

    name = (name or "").strip()
    if not name:
        return {"ok": False, "error": "le nom est requis"}

    address = (address or "").strip()
    if not address:
        return {"ok": False, "error": "l'adresse est requise"}

    path = client_file_path(uid)
    if os.path.isfile(path):
        return {"ok": False, "error": f"un client {uid!r} existe déjà"}

    color = (color or "").strip() or _random_unused_color()

    lines = [f"uid:{uid}", f"name:{name}", f"address:{address}"]
    for key, value in (("creditor", creditor), ("country", country), ("tva", tva)):
        value = (value or "").strip()
        if value:
            lines.append(f"{key}:{value}")
    lines.append(f"color:{color}")

    os.makedirs(os.path.dirname(path), exist_ok=True)
    _write_lines(path, lines)
    return {"ok": True}
