"""
Restore externals/database/ from the most recent zip in backups/.

Run from runtime/ or root on a fresh machine after cloning the repo
and dropping a backup zip into backups/.
"""

import os
import zipfile
import sys

import configs

# ─── paths ────────────────────────────────────────────────────────────────────

ROOT        = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
BACKUPS_DIR = os.path.join(ROOT, "exports", "backups")
DEST_DIR    = os.path.join(ROOT, "database")

# ─── find latest zip ──────────────────────────────────────────────────────────

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

# ─── confirm ──────────────────────────────────────────────────────────────────

dest_db = DEST_DIR
if os.path.isdir(dest_db):
    answer = input(f"\nexternals/database/ existe déjà. Écraser ? (o/N) : ").strip().lower()
    if answer != "o":
        print("annulé.")
        sys.exit(0)

# ─── extract ──────────────────────────────────────────────────────────────────

os.makedirs(DEST_DIR, exist_ok=True)
file_count = 0
with zipfile.ZipFile(zip_path, "r") as zf:
    zf.extractall(ROOT)
    file_count = len(zf.namelist())

print(f"fichiers restaurés : {file_count}")
print(f"destination        : {dest_db}")
print(f"\nLance maintenant main_billing.py pour régénérer les exports.")

if configs.pause_on_exit:
    input("\nEntrée pour fermer...")
