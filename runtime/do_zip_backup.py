"""
Zip externals/database/ → backups/YYYY-MM-DD_HH-MM.zip

Run from runtime/ or root. The backups/ folder is git-ignored.
The zip is then copied to every extra "zip" folder (cloud sync, USB key, ...)
listed on the Sauvegarde page, see modules/export_folders.py.
"""

import os
import uuid
import zipfile
import sys
from datetime import datetime

import configs
from modules import backup_state, export_folders

# ─── paths ────────────────────────────────────────────────────────────────────

ROOT        = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SOURCE_DIR  = os.path.join(ROOT, "database")
BACKUPS_DIR = export_folders.local_folder("zip")

KEEP = 20

# every zip written by write_zip() carries a short random uid + its creation
# timestamp, stored in the zip's own comment (not its filename, not a file
# inside it) so both survive the zip being renamed or copied to another backup
# folder -- the same uid showing up in two folders means it's the same backup.
# Same key:value syntax as database/ files:
#   compta-backup
#   uid:a1b2c3d4
#   created:2026-10-03 14:22:05
# Zips made before this have no comment (uid/created None).
ZIP_HEADER = "compta-backup"
CREATED_FORMAT = "%Y-%m-%d %H:%M:%S"


def read_zip_info(zf):
    """{"uid": str|None, "created": datetime|None} from an open ZipFile's
    comment, as written by write_zip()."""
    info = {"uid": None, "created": None}
    lines = zf.comment.decode("utf-8", errors="ignore").splitlines()
    if not lines or lines[0].strip() != ZIP_HEADER:
        return info
    for line in lines[1:]:
        key, sep, value = line.partition(":")
        key, value = key.strip(), value.strip()
        if not sep or not value:
            continue
        if key == "uid":
            info["uid"] = value
        elif key == "created":
            try:
                info["created"] = datetime.strptime(value, CREATED_FORMAT)
            except ValueError:
                pass
    return info


def write_zip(zip_path, created=None, action="sauvegarde"):
    """Zip database/ into zip_path (entries under database/, relative to the
    repo root), return (file_count, uid, created). Used by make_backup() and
    by the Sauvegarde page's "Exporter" button (any destination, action
    "export"). Records the zip as the database's new baseline (see
    modules/backup_state.py)."""
    uid = uuid.uuid4().hex[:8]
    created = (created or datetime.now()).replace(microsecond=0)
    file_count = 0
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.comment = f"{ZIP_HEADER}\nuid:{uid}\ncreated:{created.strftime(CREATED_FORMAT)}\n".encode("utf-8")
        for dirpath, _, filenames in os.walk(SOURCE_DIR):
            for fname in filenames:
                fpath   = os.path.join(dirpath, fname)
                arcname = os.path.relpath(fpath, ROOT)  # relatif à la racine du repo
                zf.write(fpath, arcname)
                file_count += 1
        manifest = backup_state.zip_manifest(zf)
    backup_state.record(action, uid, created, zip_path, manifest)
    return file_count, uid, created


def make_backup(open_folder=False):
    """Zip database/ into exports/backups/, prune old zips, return the zip path (or None if source is missing)."""

    if not os.path.isdir(SOURCE_DIR):
        print(f"[ERROR] dossier source introuvable : {SOURCE_DIR}")
        return None

    os.makedirs(BACKUPS_DIR, exist_ok=True)

    now       = datetime.now()
    zip_name  = f"{now.strftime('%Y-%m-%d_%H-%M-%S')}.zip"
    zip_path  = os.path.join(BACKUPS_DIR, zip_name)

    file_count, uid, created = write_zip(zip_path, now)

    size_kb = os.path.getsize(zip_path) / 1024

    print(f"\n── backup ──")
    print(f"fichiers : {file_count}")
    print(f"taille   : {size_kb:.1f} ko")
    print(f"zip      : {zip_path}")
    print(f"uid      : {uid}")
    print(f"créé le  : {created.strftime(CREATED_FORMAT)}")

    # keep only last N zips
    zips = sorted([f for f in os.listdir(BACKUPS_DIR) if f.endswith(".zip")])
    to_delete = zips[:-KEEP]
    for f in to_delete:
        os.remove(os.path.join(BACKUPS_DIR, f))
        print(f"supprimé : {f}")

    if open_folder and hasattr(os, "startfile"):
        os.startfile(os.path.normpath(BACKUPS_DIR))

    return zip_path


if __name__ == "__main__":
    zip_path = make_backup(open_folder=True)
    if zip_path is None:
        sys.exit(1)
    export_folders.copy_to("zip", zip_path)

    if configs.pause_on_exit:
        input("\nEntrée pour fermer...")
