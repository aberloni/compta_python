"""
Target folders each kind of export is copied to (cloud sync, USB key, ...),
managed on the Sauvegarde page. One group per kind of export; every export is
always written to its group's local folder first (as before), then copied to
the group's extra folders.

  zip  backups of database/  exports/backups/   do_zip_backup.make_backup()
  pdf  bill PDFs             exports/billings/  packages/export/exporter.exportBill()

Extra folders are machine-specific, so they live in runtime/backup_folders.conf
(gitignored), one `group:path` per line:
  zip:N:\\cloud\\compta
  pdf:D:\\factures
A line with no known group prefix (written before groups existed) is a zip
folder.
"""

import os
import shutil

RUNTIME_DIR  = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
ROOT         = os.path.abspath(os.path.join(RUNTIME_DIR, ".."))
FOLDERS_FILE = os.path.join(RUNTIME_DIR, "backup_folders.conf")

# group -> (label, local folder, always written to)
GROUPS = {
    "zip": ("Sauvegardes de la base (zip)", os.path.join(ROOT, "exports", "backups")),
    "pdf": ("Factures PDF",                 os.path.join(ROOT, "exports", "billings")),
}


def same_folder(a, b):
    return os.path.normcase(os.path.abspath(a)) == os.path.normcase(os.path.abspath(b))


def local_folder(group):
    return GROUPS[group][1]


# ─── conf file ────────────────────────────────────────────────────────────────

def load_all():
    """{group: [extra folder, ...]} for every group in GROUPS."""
    folders = {group: [] for group in GROUPS}
    if not os.path.isfile(FOLDERS_FILE):
        return folders
    with open(FOLDERS_FILE, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            group, sep, path = line.partition(":")
            if sep and group in GROUPS:
                folders[group].append(path.strip())
            else:
                folders["zip"].append(line)  # legacy line, no group prefix
    return folders


def load(group):
    """Extra folders of one group (its local folder not included)."""
    return load_all()[group]


def save_all(folders):
    with open(FOLDERS_FILE, "w", encoding="utf-8") as f:
        f.write("# dossiers où copier chaque export, en plus de son dossier local -- groupe:chemin, un par ligne\n")
        for group in GROUPS:
            for path in folders.get(group, []):
                f.write(f"{group}:{path}\n")


def is_known(group, folder):
    """True for the group's local folder or one of its extra folders."""
    return any(same_folder(folder, k) for k in [local_folder(group)] + load(group))


def add(group, folder):
    folders = load_all()
    folders[group].append(folder)
    save_all(folders)


def remove(group, folder):
    """Drop folder from the group's list (its files are left untouched).
    Returns False if it wasn't listed."""
    folders = load_all()
    kept = [f for f in folders[group] if not same_folder(f, folder)]
    if len(kept) == len(folders[group]):
        return False
    folders[group] = kept
    save_all(folders)
    return True


# ─── copy ─────────────────────────────────────────────────────────────────────

def copy_to(group, path):
    """Copy the file at path into every extra folder of group, same file name
    (overwrites a previous copy). Returns {"copied": [destination path, ...],
    "failed": [{"folder", "error"}, ...]}, ready to hand to the page's JS. A
    missing folder (USB key unplugged) or a failed copy is only reported, the
    local file is already written. Extra folders are never pruned or cleared."""
    copied, failed = [], []
    for folder in load(group):
        if not os.path.isdir(folder):
            failed.append({"folder": folder, "error": "dossier introuvable"})
            continue
        dest = os.path.join(folder, os.path.basename(path))
        try:
            shutil.copy2(path, dest)
        except OSError as e:
            failed.append({"folder": folder, "error": str(e)})
            continue
        copied.append(dest)
    for dest in copied:
        print(f"copié    : {dest}")
    for f in failed:
        print(f"[WARN] copie impossible vers {f['folder']} : {f['error']}")
    return {"copied": copied, "failed": failed}
