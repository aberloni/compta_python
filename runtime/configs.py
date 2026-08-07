import sys
import os

# Windows console defaults to cp1252, which can't encode the ── etc. used in
# terminal output below; force UTF-8 so those prints don't crash.
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

DB_EXTENSIONS = {
    "clients":   ".cli",
    "tasks":     ".task",
    "projects":  ".proj",
    "bills":     ".bill",
    "infos":     ".info",
    "creditors": ".cred",
    "statements":".csv",
    "wiring":    ".wire",
}

# ─── settings ─────────────────────────────────────────────────────────────────
# user-tunable settings live in settings.conf (same key:value syntax as
# database/ files) so they can be hand-edited without touching Python.

def _load_settings(path):
    settings = {}
    if not os.path.isfile(path):
        print(f"warning:settings file missing @{path}")
        return settings
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            key, sep, value = line.partition(":")
            if not sep:
                continue
            settings[key.strip()] = value.strip()
    return settings

def _bool(value, default):
    if value is None:
        return default
    return value.lower() in ("true", "1", "yes", "oui")

def _list(value, default):
    if value is None:
        return default
    return [v.strip() for v in value.split(",")]

_settings = _load_settings(os.path.join(os.path.dirname(__file__), "settings.conf"))

# billing range to export (inclusive), [start, end] as "YYYY-MM"
billingRange = _list(_settings.get("billingRange"), ["2026-05", "2026-07"])

# create pdf
creatPdf = _bool(_settings.get("creatPdf"), True)

# zip database/ to exports/backups/ before generating bills
backupBeforeBilling = _bool(_settings.get("backupBeforeBilling"), True)

# open export folder after process
openBillingFolder = _bool(_settings.get("openBillingFolder"), True)

# keep terminal open after scripts finish (set False when running from an IDE terminal that stays open)
pause_on_exit = _bool(_settings.get("pause_on_exit"), True)

# path to database/ folder at repo root
dbPath = os.path.abspath(os.path.join(os.path.dirname(__file__), "../")) + "/"

def is_debugging():
    return sys.gettrace() is not None
