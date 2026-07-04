"""
Pre-generate .task files for a full year.

Each file contains all days of the month as commented-out lines,
grouped by week, with weekends marked.
Edit the year below, then run from runtime/.
"""

import calendar
import os
from datetime import date

import configs
from modules.path import Path

# ─── config ───────────────────────────────────────────────────────────────────

YEAR = 2026  # ← change this

# ─── generate ─────────────────────────────────────────────────────────────────

out_dir = Path.getDbTypePath(__import__('packages.database.database', fromlist=['DatabaseType']).DatabaseType.tasks)

for month in range(1, 13):
    ym = f"{YEAR}-{month:02d}"
    filename = f"{ym}.task"
    filepath = os.path.join(out_dir, filename)

    if os.path.exists(filepath):
        print(f"skip  {filename}  (already exists)")
        continue

    lines = [f"# {ym}", ""]

    _, num_days = calendar.monthrange(YEAR, month)
    current_week = None

    for day in range(1, num_days + 1):
        d = date(YEAR, month, day)
        week = d.isocalendar()[1]
        weekday = d.weekday()  # 0=Mon, 6=Sun

        if week != current_week:
            if current_week is not None:
                lines.append("")
            current_week = week

        day_name = ["lun", "mar", "mer", "jeu", "ven", "sam", "dim"][weekday]
        lines.append(f"#{day:02d}:  # {day_name}")

    lines.append("")

    with open(filepath, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    print(f"wrote {filepath}")

print("done")
