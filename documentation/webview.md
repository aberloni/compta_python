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
