"""
What the current database/ is based on: the last zip written (sauvegarde,
export) or read (import / restauration). The data every view shows is that
zip + whatever was modified since.

Recorded in runtime/backup_state.conf (gitignored: machine-specific, and kept
outside database/ so a restore doesn't overwrite it) every time a zip is
written (do_zip_backup.write_zip()) or imported (do_zip_restore.restore_zip()),
together with that zip's file manifest (path -> CRC32, the same CRC the zip
stores per entry). Comparing it with the CRC32 of the files currently on disk
lists what was modified since, per file, without needing the zip itself to
still be around.

Before anything was recorded (state file missing), the baseline is guessed
from the most recent backup zip in the Sauvegarde page's folders.
"""

import os
import zipfile
import zlib
from datetime import datetime

RUNTIME_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
ROOT        = os.path.abspath(os.path.join(RUNTIME_DIR, ".."))
DB_DIR      = os.path.join(ROOT, "database")
STATE_FILE  = os.path.join(RUNTIME_DIR, "backup_state.conf")

TIME_FORMAT = "%Y-%m-%d %H:%M:%S"


# ─── manifests (zip entry path -> CRC32) ──────────────────────────────────────

def zip_manifest(zf):
    """Manifest of an open ZipFile, from the CRC32 it stores per entry."""
    return {i.filename: i.CRC for i in zf.infolist() if not i.filename.endswith("/")}


def current_manifest():
    """Manifest of database/ as it is on disk, keyed like zip entries
    (database/clients/x.cli)."""
    manifest = {}
    for dirpath, _, filenames in os.walk(DB_DIR):
        for fname in filenames:
            path = os.path.join(dirpath, fname)
            with open(path, "rb") as f:
                crc = zlib.crc32(f.read())
            manifest[os.path.relpath(path, ROOT).replace(os.sep, "/")] = crc
    return manifest


# ─── state file ───────────────────────────────────────────────────────────────

def record(action, uid, created, zip_path, manifest):
    """Remember that database/ now matches zip_path. action: "sauvegarde",
    "export" or "import". Never raises: a failure here only loses the
    "modifications" tracking, it mustn't fail the backup/import itself."""
    try:
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            f.write("# état de la base au dernier zip écrit ou importé -- généré par l'app, ne pas éditer\n")
            f.write(f"action:{action}\n")
            f.write(f"uid:{uid or ''}\n")
            f.write(f"created:{created.strftime(TIME_FORMAT) if created else ''}\n")
            f.write(f"at:{datetime.now().strftime(TIME_FORMAT)}\n")
            f.write(f"path:{zip_path}\n")
            for name, crc in sorted(manifest.items()):
                f.write(f"file:{name}={crc:08x}\n")
    except OSError as e:
        print(f"[WARN] état de sauvegarde non enregistré : {e}")


def _parse_time(value):
    try:
        return datetime.strptime(value, TIME_FORMAT)
    except ValueError:
        return None


def load():
    """Recorded baseline, or None if nothing was recorded yet:
    {"action", "uid", "created", "at", "path", "manifest", "guessed": False}."""
    if not os.path.isfile(STATE_FILE):
        return None
    state = {"action": "", "uid": None, "created": None, "at": None, "path": "",
             "manifest": {}, "guessed": False}
    with open(STATE_FILE, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            key, sep, value = line.partition(":")
            if not sep:
                continue
            if key == "file":
                name, _, crc = value.rpartition("=")
                state["manifest"][name] = int(crc, 16)
            elif key in ("created", "at"):
                state[key] = _parse_time(value)
            elif key in ("action", "path"):
                state[key] = value
            elif key == "uid":
                state["uid"] = value or None
    return state


def baseline():
    """load(), or when nothing was recorded yet, the most recent backup zip
    found in the Sauvegarde page's folders ("guessed": True). None if neither."""
    state = load()
    if state:
        return state
    from do_zip_restore import list_backups  # lazy: do_zip_* import this module
    for b in list_backups():
        if b.files is None:
            continue
        path = os.path.join(b.folder, b.name)
        with zipfile.ZipFile(path, "r") as zf:
            manifest = zip_manifest(zf)
        return {"action": "sauvegarde", "uid": b.uid, "created": b.date, "at": None,
                "path": path, "manifest": manifest, "guessed": True}
    return None


# ─── what views show ──────────────────────────────────────────────────────────

def pending_changes(state):
    """Files changed since the baseline: {"modified", "added", "removed"},
    each a sorted list of paths relative to database/."""
    current, saved = current_manifest(), state["manifest"]
    strip = lambda names: sorted(n[len("database/"):] if n.startswith("database/") else n for n in names)
    return {
        "modified": strip(n for n in current if n in saved and current[n] != saved[n]),
        "added":    strip(n for n in current if n not in saved),
        "removed":  strip(n for n in saved if n not in current),
    }


def summary_text(state):
    """'2026-10-03 15:54 (aujourd'hui, export, uid 5eac6838)' for the
    baseline's zip, or 'aucune'. The date is the zip's creation date, i.e.
    when the data now on disk (before any later modification) was saved."""
    if not state or not state["created"]:
        return "aucune"
    created = state["created"]
    days = (datetime.now().date() - created.date()).days
    age = "aujourd'hui" if days <= 0 else "hier" if days == 1 else f"il y a {days} jours"
    details = [age, state["action"]] + ([f"uid {state['uid']}"] if state["uid"] else [])
    return f"{created.strftime('%Y-%m-%d %H:%M')} ({', '.join(details)})"
