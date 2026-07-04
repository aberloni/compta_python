"""
Zip externals/database/ → backups/YYYY-MM-DD_HH-MM.zip

Run from runtime/ or root. The backups/ folder is git-ignored.
Copy the zip to your cloud manually for off-machine backup.
"""

import os
import zipfile
import sys
from datetime import datetime

import configs

# ─── paths ────────────────────────────────────────────────────────────────────

ROOT        = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SOURCE_DIR  = os.path.join(ROOT, "database")
BACKUPS_DIR = os.path.join(ROOT, "exports", "backups")

# ─── checks ───────────────────────────────────────────────────────────────────

if not os.path.isdir(SOURCE_DIR):
    print(f"[ERROR] dossier source introuvable : {SOURCE_DIR}")
    sys.exit(1)

os.makedirs(BACKUPS_DIR, exist_ok=True)

# ─── zip ──────────────────────────────────────────────────────────────────────

timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
zip_name  = f"{timestamp}.zip"
zip_path  = os.path.join(BACKUPS_DIR, zip_name)

file_count = 0
with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
    for dirpath, _, filenames in os.walk(SOURCE_DIR):
        for fname in filenames:
            fpath   = os.path.join(dirpath, fname)
            arcname = os.path.relpath(fpath, ROOT)  # relatif à la racine du repo
            zf.write(fpath, arcname)
            file_count += 1

size_kb = os.path.getsize(zip_path) / 1024

print(f"\n── backup ──")
print(f"fichiers : {file_count}")
print(f"taille   : {size_kb:.1f} ko")
print(f"zip      : {zip_path}")

# ─── keep only last N zips ────────────────────────────────────────────────────

KEEP = 20
zips = sorted([f for f in os.listdir(BACKUPS_DIR) if f.endswith(".zip")])
to_delete = zips[:-KEEP]
for f in to_delete:
    os.remove(os.path.join(BACKUPS_DIR, f))
    print(f"supprimé : {f}")

if hasattr(os, "startfile"):
    os.startfile(os.path.normpath(BACKUPS_DIR))

if configs.pause_on_exit:
    input("\nEntrée pour fermer...")
