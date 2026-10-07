"""
Restore externals/database/ from the most recent zip in backups/.

Run from runtime/ or root on a fresh machine after cloning the repo
and dropping a backup zip into backups/.

restore_zip() is also what the Sauvegarde page (view_backups.py) calls to
import any zip: the current database/ is zipped to exports/backups/ first,
then replaced as a whole by the zip's content (files absent from the zip
don't survive), so an import can always be undone by restoring that zip.
"""

import os
import shutil
import tempfile
import zipfile
import sys
from collections import namedtuple
from datetime import datetime

import configs
import do_zip_backup
from modules import backup_state, export_folders

# ─── paths ────────────────────────────────────────────────────────────────────

ROOT        = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
BACKUPS_DIR = os.path.join(ROOT, "exports", "backups")
DEST_DIR    = os.path.join(ROOT, "database")
WORK_DIR    = os.path.join(ROOT, "exports")  # same drive as database/, so os.rename works


def inspect_zip(zip_path):
    """Check zip_path is a database backup (every file under database/, no
    path escaping it). Returns {"ok": True, "files": n, "uid": uid|None,
    "created": datetime|None} or {"ok": False, "error": ...} -- uid/created
    from the zip comment, see do_zip_backup.write_zip()."""
    if not os.path.isfile(zip_path):
        return {"ok": False, "error": f"fichier introuvable : {zip_path}"}
    if not zipfile.is_zipfile(zip_path):
        return {"ok": False, "error": "ce fichier n'est pas un zip valide"}
    with zipfile.ZipFile(zip_path, "r") as zf:
        files = [n for n in zf.namelist() if not n.endswith("/")]
        info = do_zip_backup.read_zip_info(zf)
    if not files:
        return {"ok": False, "error": "le zip est vide"}
    for name in files:
        parts = name.replace("\\", "/").split("/")
        if parts[0] != "database" or ".." in parts:
            return {"ok": False, "error": f"le zip contient un fichier hors de database/ : {name}"}
    return {"ok": True, "files": len(files), "uid": info["uid"], "created": info["created"]}


# ─── backups across folders ───────────────────────────────────────────────────
# what the Sauvegarde page lists

# date: creation timestamp from the zip comment, else zip_date() (older zips)
# files: database file count, None if not a database backup zip
# uid: see do_zip_backup.write_zip(), None for zips made before uids existed
Backup = namedtuple("Backup", "folder is_local name date files size uid")


def fmt_created(created):
    """Creation datetime as text (for the page's JS, which can't take a
    datetime), or None."""
    return created.strftime(do_zip_backup.CREATED_FORMAT) if created else None


def backup_folders():
    """(path, is_local) -- local exports/backups/ always first, then extra folders."""
    return [(BACKUPS_DIR, True)] + [(f, False) for f in export_folders.load("zip")]


def folder_label(path, is_local):
    return "local" if is_local else (os.path.basename(os.path.normpath(path)) or path)


def zip_date(name, path):
    """Fallback date for zips with no creation timestamp in their comment
    (made before uids existed): from the name ending in
    YYYY-MM-DD_HH-MM-SS.zip, else file mtime."""
    try:
        return datetime.strptime(name[:-4][-19:], "%Y-%m-%d_%H-%M-%S")
    except ValueError:
        return datetime.fromtimestamp(os.path.getmtime(path))


def list_backups():
    """Every backup zip found in backup_folders(), newest first. Local folder:
    every zip (invalid ones with files=None); extra folders: only actual
    database backups, unrelated zips in a shared folder are skipped."""
    backups = []
    for folder, is_local in backup_folders():
        if not os.path.isdir(folder):
            continue
        for name in os.listdir(folder):
            path = os.path.join(folder, name)
            if not name.lower().endswith(".zip") or not os.path.isfile(path):
                continue
            try:
                check = inspect_zip(path)
            except Exception:
                check = {"ok": False}
            files = check["files"] if check["ok"] else None
            if files is None and not is_local:
                continue
            date = check.get("created") or zip_date(name, path)
            backups.append(Backup(folder, is_local, name, date, files,
                                  os.path.getsize(path), check.get("uid")))
    backups.sort(key=lambda b: b.date, reverse=True)
    return backups


def restore_zip(zip_path):
    """Replace database/ by the content of zip_path. Extracts to a temp folder
    first (so a bad zip never touches the live database), then zips the
    current database/ to exports/backups/, then swaps the folders.
    Returns {"ok": True, "files": n, "uid": uid|None, "safety_backup": path|None} or {"ok": False, "error": ...}."""
    check = inspect_zip(zip_path)
    if not check["ok"]:
        return check

    os.makedirs(WORK_DIR, exist_ok=True)
    work = tempfile.mkdtemp(prefix="import_", dir=WORK_DIR)
    try:
        with zipfile.ZipFile(zip_path, "r") as zf:
            zf.extractall(os.path.join(work, "new"))
            manifest = backup_state.zip_manifest(zf)
        new_db = os.path.join(work, "new", "database")

        # backup only after extracting: make_backup() prunes old zips, which
        # could otherwise delete zip_path itself if it's the oldest one
        safety_backup = do_zip_backup.make_backup() if os.path.isdir(DEST_DIR) else None

        old_db = os.path.join(work, "old")
        if os.path.isdir(DEST_DIR):
            os.rename(DEST_DIR, old_db)
        try:
            os.rename(new_db, DEST_DIR)
        except Exception:
            if os.path.isdir(old_db):
                os.rename(old_db, DEST_DIR)
            raise
    except Exception as e:
        return {"ok": False, "error": str(e)}
    finally:
        shutil.rmtree(work, ignore_errors=True)

    # after the safety backup above, which recorded itself as the baseline
    created = check["created"] or zip_date(os.path.basename(zip_path), zip_path)
    backup_state.record("import", check["uid"], created, zip_path, manifest)

    print(f"\n── restore ──")
    print(f"zip source         : {zip_path}")
    print(f"uid                : {check['uid']}")
    print(f"fichiers restaurés : {check['files']}")
    print(f"ancienne base      : {safety_backup}")
    return {"ok": True, "files": check["files"], "uid": check["uid"],
            "created": fmt_created(check["created"]), "safety_backup": safety_backup}


if __name__ == "__main__":

    # ─── find latest zip ──────────────────────────────────────────────────────

    if not os.path.isdir(BACKUPS_DIR):
        print(f"[ERROR] dossier backups/ introuvable : {BACKUPS_DIR}")
        sys.exit(1)

    zips = sorted([f for f in os.listdir(BACKUPS_DIR) if f.endswith(".zip")])
    if not zips:
        print("[ERROR] aucun zip trouvé dans backups/")
        sys.exit(1)

    latest   = zips[-1]
    zip_path = os.path.join(BACKUPS_DIR, latest)

    print(f"\n── restore ──")
    print(f"zip source : {latest}")

    # ─── confirm ──────────────────────────────────────────────────────────────

    if os.path.isdir(DEST_DIR):
        answer = input(f"\ndatabase/ existe déjà. Écraser ? (o/N) : ").strip().lower()
        if answer != "o":
            print("annulé.")
            sys.exit(0)

    # ─── extract ──────────────────────────────────────────────────────────────

    result = restore_zip(zip_path)
    if not result["ok"]:
        print(f"[ERROR] {result['error']}")
        sys.exit(1)

    print(f"destination        : {DEST_DIR}")
    print(f"\nLance maintenant main_billing.py pour régénérer les exports.")

    if configs.pause_on_exit:
        input("\nEntrée pour fermer...")
