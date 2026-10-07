# Webview app wrapper

Goal: a "desktop app" feel around the existing entry-point scripts (`do_billing.py`, `shell_tva.py`, `shell_unpaid.py`, `shell_workdays.py`, `view_*.py`, ...) without turning them into a service.

## Decisions

- **No server.** `pywebview` opens a native OS window pointing at a local HTML file (or inline HTML string). No Flask / `http.server` / sockets. UI ↔ Python communication goes through pywebview's own `js_api` bridge (JS calls a Python method directly, in-process).
- **No repo restructuring for install/run.** After `git clone`: `pip install -r requirements.txt` (adds `pywebview`), then `python app_gui.py` from `runtime/`. One new entry point added alongside the existing ones — nothing else changes.
- **Scripts stay independent and unmodified**, runnable by hand exactly as today. The webview never imports them in-process — it launches each one as a **subprocess** (`subprocess.Popen`), the same way a user would from a terminal, and streams stdout back into the window.
  - Reason: entry-point scripts are top-level modules that call `exit()` at the end (e.g. [do_billing.py](../runtime/do_billing.py)) and some block on `input()` (e.g. [shell_unpaid.py](../runtime/shell_unpaid.py)). Importing them in-process would kill the webview's own Python process, or hang it. Subprocess isolation sidesteps both without touching the scripts.
  - Trade-off accepted: only print-style progress is available back to the UI (stdout stream), not structured return values. If a script later needs to hand back structured data, that's a script-level change (e.g. writing a small JSON result file it already writes for `.dump` output), not a webview-level one.
- **Config stays in `settings.conf` / `configs.py`.** The webview's job is to gather input (e.g. billing range) and write it into `settings.conf` before launching the relevant script, not to invent a parallel config path.

- **Every page in the webview is the output of a `view_*.py` script.** There is no page written by hand — the homepage included. This keeps "generate a page" a single mental model across the whole app.
- **Shared header/footer via a plain Python helper, not a template engine.** [modules/layout.py](../runtime/modules/layout.py) exposes `render_shell(title, active_file, body_html, extra_style)`: it wraps a page's own body content and page-specific `<style>` rules with a common nav bar (links to every generated page, current one highlighted) and footer. Each `view_*.py` still owns its own layout/CSS for its content — only the outer shell is shared. `PAGES` in that module is the single place that lists all pages and their nav labels.

## Built so far

- [modules/layout.py](../runtime/modules/layout.py) — shared shell (nav + footer).
- [view_homepage.py](../runtime/view_homepage.py) — new landing page (`exports/view/homepage.html`), one card per existing view page.
- All 7 existing `view_*.py` scripts (`billing`, `tva`, `trimester`, `tasks` (summary), `tasks_project`, `tasks_calendar`, `wiring`) now call `render_shell(...)` instead of building their own full `<html>` document. Their own content/CSS is unchanged — only the outer wrapper moved to `layout.py`.

Verified by running every `view_*.py` from `runtime/` and inspecting the generated HTML; `view_trimester.py` fails with `ModuleNotFoundError: packages.database.impots` — pre-existing, unrelated to this work (the module doesn't exist in the repo).

- [app_gui.py](../runtime/app_gui.py) — the actual entry point. On launch it regenerates `homepage.html` (subprocess call to `view_homepage.py`, same as a user would run it) then opens it in a `pywebview` window and blocks until closed.
- **`configs.webview_mode`** (`runtime/configs.py`) — `True` when the env var `COMPTA_WEBVIEW=1` is set. `app_gui.py` sets it only on the subprocess it launches. Every `view_*.py` script checks it in exactly two places, unchanged otherwise: skip `os.startfile(...)` (don't pop a second OS-default-browser window — the webview already shows the page) and skip the trailing `input("\nEntrée pour fermer...")` (no interactive stdin from a webview-launched subprocess, so it would just hang). Run by hand from a terminal, `webview_mode` is `False` and both behave exactly as before.
- `requirements.txt` added under `runtime/` (`weasyprint`, `python-dateutil`, `pdfplumber`, `pywebview`) — the repo had no dependency file before this.

Verified: ran `app_gui.py` directly — it regenerates the homepage silently (no prompt, no stray browser window) and opens the pywebview window, which stays open until closed with no leftover process.

## Auto-refresh toggle

- A checkbox in the nav ("Auto refresh"), ON by default, present on every generated page since it's part of the shared shell.
- State lives in `app_gui.py`'s `Api` object (a plain instance attribute), not in the page — pages are static files and can't hold live state themselves. Every nav/card link calls `navigateTo(file)` (in [modules/layout.py](../runtime/modules/layout.py)), which calls `pywebview.api.navigate(file)`; `Api.navigate()` decides whether to re-run that page's script first:
  - **ON** → always re-run the script, then load the (fresh) file.
  - **OFF** → load the file as-is; only run the script if the file doesn't exist yet (first visit to a page never generated this session).
- Checkbox reflects the real state via the `pywebviewready` event (fires once `pywebview.api` is injected) calling `Api.get_auto_refresh()`; toggling it calls `Api.set_auto_refresh()`. State resets to ON every time `app_gui.py` restarts — not persisted to disk (not asked for, and it's a session-level preference, not data).
- Outside the webview (a generated page opened directly as a file), `pywebview.api` doesn't exist, so `navigateTo()` falls back to a plain `window.location.href` — links keep working, just without refresh/toggle behavior, consistent with pages staying independently viewable.

Verified: all `view_*.py` scripts still regenerate cleanly under `COMPTA_WEBVIEW=1`; the generated HTML carries the expected `navigateTo`/toggle markup and script. Did not verify by clicking inside the actual native window — this sandbox can drive the separate Chromium preview pane but not the pywebview/WebView2 window itself, and a background console showed unrelated COM/accessibility errors from the sandbox's own UI-automation layer probing the WinForms window (recursion in an accessibility walker, thread-affinity errors on `CoreWebView2Controller`) — noise from this environment, not exceptions raised by our code, but worth a real click-through on your machine before relying on it.

## Error banner

- `Api.navigate()`/`Api.run()` capture the script's stderr; on non-zero exit, `Api.errors[filename]` gets the last stderr line, cleared on the next successful run of that file.
- Each page reads `get_error(CURRENT_FILE)` on `pywebviewready` and shows a red `#error-banner` div (hidden by default) if there's a message. `CURRENT_FILE` is baked into each page by `render_shell`.

## Open / not yet decided

- Whether some scripts should grow CLI args (`argparse`) so the webview can pass one-off parameters without touching `settings.conf` (which is shared, persistent state).
- How the "run a script" actions (billing export, tva, etc.) get triggered from inside the webview — next step, per the subprocess-launch decision above. Will reuse the same `COMPTA_WEBVIEW` env var so those scripts also skip their terminal-only prompts/side-effects when launched this way.
- Whether other pages (billing, tva, ...) should also be regenerated up front like the homepage, or only on demand when their nav link/action is used.

## Calendrier page — open task file

- An **Ouvrir YYYY-MM.task** button (year row, right side) follows the month on screen and calls `Api.open_task_file(ym)`: `os.startfile()` on `database/tasks/{ym}.task` (path from `tools/calendar_export.task_file_path()`). A missing file is created first with only its `# YYYY-MM` header, same as `write_task_entry()` does. `ym` must match `YYYY-MM`.

## TVA / Trimestres pages — open declarations file

- An **Ouvrir YYYY.tva** button on the TVA page (header, left of "Déclarer sur impots.gouv") and an **Ouvrir YYYY.urssaf** button on the Trimestres page (left of "Déclarer sur l'URSSAF") call `Api.open_declaration_file(kind, year)` for the current year. It opens `database/{kind}/{year}.{kind}`, where `kind` is `"tva"` or `"urssaf"`. A missing file is created first with a single comment line describing the format. `open_task_file()` and `open_declaration_file()` share `_open_data_file(path, header)`, which creates the file if needed and then calls `os.startfile()`.

## Calendrier page — import preview, local-only rows

- `Api.fetch_calendar_preview(ym)` also returns the `.task` file entries with no calendar event on the same `(day, uid)`, as rows with `local: "missing"` / `status: "local"` (empty title, `fraction` = the local value). Rows are sorted by date. They have no action button, a blue row background and the "Absent du calendrier" label, and they're counted in the differences banner next to the conflicts. An event with no resolved uid (ignored, unmatched) covers nothing, so a local entry that day still shows up as missing.

## Sauvegarde page (import / export zip)

- [view_backups.py](../runtime/view_backups.py) → `backups.html`, last entry of the edit group in the nav.
- **Exporter…** → `Api.export_database()`: save dialog, then `do_zip_backup.write_zip(path)` (same zip layout as the backups: entries under `database/`).
- **Importer…** → `Api.pick_import_file()` (open dialog + `do_zip_restore.inspect_zip()` check), JS `confirm()`, then `Api.import_database(path)` → `do_zip_restore.restore_zip()`.
- Each local zip in `exports/backups/` has a **Restaurer** button → `Api.restore_backup(name)` (same restore path).
- `restore_zip()` **replaces** `database/` as a whole (files missing from the zip are gone afterwards), never merges. Order: validate the zip (every entry under `database/`, no `..`) → extract to a temp dir under `exports/` → `make_backup()` of the current database (safety zip, listed on the page) → swap the folders with `os.rename`, then roll back if the second rename fails. The backup runs after extraction on purpose: `make_backup()` prunes down to `KEEP` zips and could otherwise delete the zip being restored.
- `do_zip_restore.py` run by hand goes through the same `restore_zip()`, so it now replaces the folder instead of extracting over it.
- **Export folders, per group** ([modules/export_folders.py](../runtime/modules/export_folders.py)): the page's "Dossiers d'export" section has one block per kind of export. `GROUPS` maps each group to a label and its local folder: `zip` → `exports/backups/`, `pdf` → `exports/billings/`. Exports are always written to the local folder (unchanged), then `export_folders.copy_to(group, path)` copies the file, under the same name, to every extra folder of that group. It returns `{"copied": [...], "failed": [{"folder", "error"}]}`, and a missing folder or a failed copy never fails the export itself. `zip` copies are made by `Api.backup_database()` (and `do_zip_backup.py` run by hand). They're not made for `backupBeforeBilling` or pre-import safety backups. `pdf` copies are made by `exporter.exportBill()`, i.e. both the full billing run and the "PDF" button on Éditer factures, whose row status shows the copy count. Extra folders are added with a folder dialog (`Api.add_export_folder(group)`) and removed with `Api.remove_export_folder(group, folder)`, which only drops them from the list. They're stored as `group:path` lines in `runtime/backup_folders.conf`, gitignored because the paths are machine-specific. Lines with no group prefix (the old format) count as `zip`. In extra `zip` folders, only zips that pass `inspect_zip()` are listed, so unrelated zips in a shared cloud folder are skipped. A missing folder (e.g. an unplugged USB key) stays in the list and shows as "introuvable". `restore_backup(folder, name)` and `open_export_folder(group, folder)` refuse any folder that isn't in the group's list. Extra folders are never pruned or cleared: `KEEP` only applies to `exports/backups/`, and the billing run's clean-up only applies to `exports/billings/`.
- **Dernière sauvegarde**: `do_zip_restore.latest_backup_text()` gives the most recent zip from `list_backups()` (all folders, invalid zips ignored), using the date in the file name, or the file's mtime when the name has none. It's shown at the top of the Sauvegarde page and in the homepage footer (`render_shell(..., footer_html=...)`, an optional extra footer line only the homepage uses).
- The navbar zip button was removed (2026-10-03): backups are made from the Sauvegarde page (`Api.backup_database()`, which no longer opens the folder).
- **Backup UID + creation timestamp**: `do_zip_backup.write_zip()` writes them in the zip's archive comment (key:value lines: `compta-backup` / `uid:a1b2c3d4` / `created:YYYY-MM-DD HH:MM:SS`) and `read_zip_info()` reads them back. They're kept outside the filename so they survive renames and copies, and outside the archive entries so `inspect_zip()`/`restore_zip()` still see only `database/`. `list_backups()` uses `created` as the backup date, falling back to `zip_date()` (file name / mtime) for older zips with no comment. `fmt_created()` turns it into text for the JS bridge, since pywebview can't serialize a datetime.
- **Baseline + unsaved modifications** ([modules/backup_state.py](../runtime/modules/backup_state.py)): the data on disk = the last zip written or imported + modifications since. `write_zip()` (backup, export, pre-import safety backup, backupBeforeBilling) and `restore_zip()` call `backup_state.record()`, which writes `runtime/backup_state.conf`. That file is gitignored and kept outside `database/` so a restore doesn't overwrite it. It holds action/uid/created/at/path plus a manifest (`file:database/…=crc32`, taken from the zip's own per-entry CRC). `pending_changes()` compares that manifest with the CRC32 of the files on disk and returns modified/added/removed, so the zip doesn't need to still exist. With no state file yet, `baseline()` guesses from the most recent valid zip in the listed folders (`guessed: True`, flagged on the page). `summary_text()` is the "Dernière sauvegarde" line: it's in every page's footer (built into `render_shell()`, which replaces the homepage-only `footer_html`) and at the top of the Sauvegarde page, above the modifications block.
