"""
Fetch a Google Calendar (read-only, via its secret iCal feed) and preview
what would be injected into database/tasks/{YYYY-MM}.task.

Running this script only prints a preview table, it never writes anything.
Writing is done one entry at a time via write_task_entry() below, used by the
Calendrier page's "Importer" buttons (see app_gui.py).

Calendar convention expected:
    Project              -> full day (1) on that project
    Project, 0.5          -> half day on that project
    Project, 0            -> worked but excluded from billing (len 0)
    off                   -> non-billable day, written as-is to the .task file

Setup:
    database/infos/calendar.info must contain:
        ical_url:https://calendar.google.com/calendar/ical/.../basic.ics
    (Settings > your calendar > Integrate calendar > "Secret address in iCal format")

Usage (run from runtime/):
    python -m tools.calendar_export [YYYY-MM]
    (defaults to the current month if omitted)
"""

import os
import re
import sys
import calendar as pycalendar
from datetime import date, datetime, timedelta, time

try:
    import requests
    from icalendar import Calendar
    from dateutil.rrule import rrulestr
except ImportError:
    sys.exit("Dépendance manquante : pip install requests icalendar python-dateutil")

import configs
from modules.assocs import Assoc
from modules.path import Path
from packages.database.database import Database, DatabaseType

# ─── config ─────────────────────────────────────────────────────────────────

# reserved uid recognized directly by name, not a real project
SPECIAL_UIDS = {"off"}

# events whose title starts with one of these (case-insensitive) are personal
# reminders, not work days — skip them entirely (e.g. "TVA" = declaration due
# reminder, not a day worked on a project called TVA). Titles starting with
# "(" are also always ignored, e.g. "(rdv dentiste)".
IGNORE_PREFIXES = [
    "TVA",
]

# work days are tracked as all-day events; timed events (meetings, calls...)
# are ignored by default since they aren't the day-tracking convention
ALL_DAY_ONLY = True

# named fraction labels, for titles like "merlies preshot" or "merlies,preshot"
# where the word describes a [0,1] time value instead of a plain number/ratio
FRACTION_LABELS = {
    "preshot": 1.0,
}

WEEKDAY_FR = ["lun", "mar", "mer", "jeu", "ven", "sam", "dim"]

# ─── fetch & parse ──────────────────────────────────────────────────────────

def load_ical_url():
    cal_info = Assoc("calendar", DatabaseType.infos)
    url = cal_info.filterKey("ical_url")
    if not url:
        sys.exit("error: ical_url missing in database/infos/calendar.info")
    return url


def fetch_ics(url):
    resp = requests.get(url, timeout=15)
    resp.raise_for_status()
    return resp.content


def parse_fraction(token):
    """Mirror Task._parse_modifier semantics (packages/database/task.py),
    plus named FRACTION_LABELS aliases (e.g. 'preshot' -> 1.0)."""
    token = token.strip()
    if token.lower() in FRACTION_LABELS:
        return FRACTION_LABELS[token.lower()]
    if token in ("0", "0.0"):
        return 0.0
    if "." in token:
        try:
            return float(token)
        except ValueError:
            return None
    if "/" in token:
        a, b = token.split("/", 1)
        try:
            a, b = int(a), int(b)
            return 0.0 if b == 0 else a / b
        except ValueError:
            return None
    return None


def parse_title(raw_title):
    """
    'merlies' -> ('merlies', 1.0)
    '1/2 merlies' or 'merlies 1/2' -> ('merlies', 0.5)   (fraction token can be a prefix or suffix)
    'merlies, 0.5' -> ('merlies', 0.5)                    (comma form also accepted)
    """
    tokens = raw_title.replace(",", " ").split()
    fraction = 1.0
    label_tokens = []
    fraction_found = False
    for token in tokens:
        if not fraction_found:
            parsed = parse_fraction(token)
            if parsed is not None:
                fraction = parsed
                fraction_found = True
                continue
        label_tokens.append(token)
    return " ".join(label_tokens).strip(), fraction


def expand_recurring(component, summary, range_start, range_end):
    dtstart = component.get("DTSTART").dt
    is_all_day = not isinstance(dtstart, datetime)
    if is_all_day:
        dtstart_dt = datetime(dtstart.year, dtstart.month, dtstart.day)
    else:
        # drop tzinfo: only the calendar date matters here, and rrulestr/between
        # need naive datetimes to compare against our naive range bounds
        dtstart_dt = dtstart.replace(tzinfo=None)

    if ALL_DAY_ONLY and not is_all_day:
        return []

    rrule_prop = component.get("RRULE")
    rule = rrulestr(f"RRULE:{rrule_prop.to_ical().decode()}", dtstart=dtstart_dt)

    exdates = set()
    exdate_prop = component.get("EXDATE")
    if exdate_prop:
        items = exdate_prop if isinstance(exdate_prop, list) else [exdate_prop]
        for item in items:
            for d in item.dts:
                exdates.add(d.dt.date() if isinstance(d.dt, datetime) else d.dt)

    range_start_dt = datetime.combine(range_start, time.min)
    range_end_dt = datetime.combine(range_end, time.max)

    events = []
    for occ in rule.between(range_start_dt, range_end_dt, inc=True):
        occ_date = occ.date()
        if occ_date not in exdates:
            events.append((occ_date, summary))
    return events


def is_ignored(raw_title):
    title = raw_title.strip()
    if title.startswith("("):
        return True
    title = title.lower()
    return any(title.startswith(prefix.lower()) for prefix in IGNORE_PREFIXES)


def parse_events(ics_bytes, range_start, range_end):
    cal = Calendar.from_ical(ics_bytes)
    events = []

    for component in cal.walk("VEVENT"):
        status = component.get("STATUS")
        if status and str(status).upper() == "CANCELLED":
            continue

        summary = str(component.get("SUMMARY", "")).strip()
        if not summary:
            continue

        if component.get("RRULE"):
            try:
                events.extend(expand_recurring(component, summary, range_start, range_end))
            except Exception as e:
                print(f"WARN: could not expand recurring event {summary!r}: {e}")
            continue

        dtstart = component.get("DTSTART").dt
        dtend_prop = component.get("DTEND")
        dtend = dtend_prop.dt if dtend_prop else None
        is_all_day = not isinstance(dtstart, datetime)

        if ALL_DAY_ONLY and not is_all_day:
            continue

        if is_all_day and dtend and (dtend - dtstart).days > 1:
            d = dtstart
            while d < dtend:  # DTEND is exclusive for all-day events
                if range_start <= d <= range_end:
                    events.append((d, summary))
                d += timedelta(days=1)
        else:
            d = dtstart.date() if isinstance(dtstart, datetime) else dtstart
            if range_start <= d <= range_end:
                events.append((d, summary))

    events.sort(key=lambda e: e[0])
    return events

# ─── project matching ───────────────────────────────────────────────────────

def build_matchers(db=None):
    if db is None:
        db = Database.init_billing()
    uid_map = {p.uid.lower(): p.uid for p in db.projects if p.uid}
    name_map = {p.name.lower(): p.uid for p in db.projects if p.name}
    return uid_map, name_map


def match_label(label, uid_map, name_map):
    key = label.strip().lower()
    if key in SPECIAL_UIDS:
        return key, "alias"
    if key in uid_map:
        return uid_map[key], "uid"
    if key in name_map:
        return name_map[key], "name"

    # soft match: a known uid appears as a whole word inside a noisier title
    # (e.g. "montage CONVATEC", "roi (radio france)") -- needs manual confirmation
    for uid_lower, uid in uid_map.items():
        if re.search(rf"\b{re.escape(uid_lower)}\b", key):
            return uid, "fuzzy?"

    return None, "UNMATCHED"


def resolve_event(raw_title, uid_map, name_map):
    """(uid, fraction, status) for one event title -- shared by the CLI
    preview and the Calendrier tab's on-demand fetch (see app_gui.py)."""
    if is_ignored(raw_title):
        return None, 1.0, "ignored"
    label, fraction = parse_title(raw_title)
    uid, status = match_label(label, uid_map, name_map)
    return uid, fraction, status

# ─── writing (Importer buttons, see app_gui.py) ─────────────────────────────

def format_modifier(fraction):
    if fraction == 1.0:
        return ""
    if fraction == 0:
        return " 0"
    return f" {fraction:g}"


def task_file_path(ym):
    return os.path.join(Path.getDbTypePath(DatabaseType.tasks), f"{ym}.task")


def parse_existing_lines(lines):
    """{(day, uid): fraction} already present in a .task file's raw lines.
    A day can have several (uid) entries (split days across projects) --
    only an identical (day, uid) pair counts as "already declared"."""
    entries = {}
    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        key, sep, value = stripped.partition(":")
        if not sep or not key.strip().isdigit():
            continue
        day = int(key.strip())
        tokens = value.split("#", 1)[0].split()
        if not tokens:
            continue
        uid = tokens[0]
        fraction = 1.0
        for token in tokens[1:]:
            parsed = parse_fraction(token)
            if parsed is not None:
                fraction = parsed
                break
        entries[(day, uid)] = fraction
    return entries


def read_existing_entries(ym):
    """{(day, uid): fraction} already declared in database/tasks/{ym}.task."""
    path = task_file_path(ym)
    if not os.path.isfile(path):
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return parse_existing_lines(f.read().splitlines())


def line_day(line):
    """Day number of a .task line, whether active or commented out (the
    template placeholders routine_tasks.py generates), else None."""
    stripped = line.strip().lstrip("#").strip()
    key, sep, _ = stripped.partition(":")
    key = key.strip()
    return int(key) if sep and key.isdigit() else None


def _write_lines(path, lines):
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n" if lines else "")


def write_task_entry(ym, day, uid, fraction, replace=False):
    """Write one day/project/fraction entry to database/tasks/{ym}.task,
    creating the file if needed, keeping entries in day order.
    - nothing declared yet for (day, uid): inserted in chronological order,
      right after any existing entries for that same day.
    - already declared with the same fraction: no-op, reports skipped.
    - already declared with a DIFFERENT fraction: left untouched and reports
      a conflict, unless replace=True (the UI confirms with the user first),
      in which case that line's value is rewritten in place."""
    path = task_file_path(ym)

    existing = ""
    if os.path.isfile(path):
        with open(path, "r", encoding="utf-8") as f:
            existing = f.read()

    lines = existing.splitlines()
    current = parse_existing_lines(lines).get((day, uid))

    if current is not None and abs(current - fraction) < 1e-9:
        return {"ok": True, "skipped": True}

    if current is not None and not replace:
        return {"ok": False, "conflict": True, "existing_fraction": current}

    os.makedirs(os.path.dirname(path), exist_ok=True)
    day_str = f"{day:02d}"

    if current is not None:
        # replace: rewrite the matching line's value in place, same position
        for idx, line in enumerate(lines):
            stripped = line.strip()
            if stripped and not stripped.startswith("#"):
                key, sep, value = stripped.partition(":")
                if sep and key.strip() == day_str:
                    value_wo_comment, hash_sign, comment = value.partition("#")
                    if value_wo_comment.split()[:1] == [uid]:
                        suffix = f" #{comment}" if hash_sign else ""
                        lines[idx] = f"{day_str}: {uid}{format_modifier(fraction)}{suffix}"
                        break
        _write_lines(path, lines)
        return {"ok": True, "skipped": False, "replaced": True}

    if not existing.strip():
        lines = [f"# {ym}", ""]

    # insert in chronological order: right after the last existing entry for
    # the same day, or right before the first entry for a later day
    days = [line_day(l) for l in lines]
    same_day = [i for i, d in enumerate(days) if d == day]
    if same_day:
        insert_at = same_day[-1] + 1
    else:
        later = [i for i, d in enumerate(days) if d is not None and d > day]
        insert_at = later[0] if later else len(lines)
    lines.insert(insert_at, f"{day_str}: {uid}{format_modifier(fraction)}")

    _write_lines(path, lines)
    return {"ok": True, "skipped": False}

# ─── main ───────────────────────────────────────────────────────────────────

def month_range(ym):
    year, month = (int(x) for x in ym.split("-"))
    start = date(year, month, 1)
    end = date(year, month, pycalendar.monthrange(year, month)[1])
    return start, end


def main():
    ym = sys.argv[1] if len(sys.argv) > 1 else date.today().strftime("%Y-%m")
    range_start, range_end = month_range(ym)

    url = load_ical_url()
    ics_bytes = fetch_ics(url)
    events = parse_events(ics_bytes, range_start, range_end)
    uid_map, name_map = build_matchers()

    print(f"\n{ym}  ({range_start} → {range_end})   {len(events)} event(s)\n")
    print(f"{'DATE':16}  {'RAW TITLE':30}  {'UID':12}  {'FRAC':5}  STATUS")
    print("-" * 80)

    unmatched = 0
    for event_date, raw_title in events:
        uid, fraction, status = resolve_event(raw_title, uid_map, name_map)
        if status == "UNMATCHED":
            unmatched += 1
        weekday = WEEKDAY_FR[event_date.weekday()]
        date_str = f"{event_date} ({weekday})"
        print(f"{date_str:16}  {raw_title[:30]:30}  {(uid or '???'):12}  {fraction:<5}  {status}")

    print("-" * 80)
    print(f"{len(events)} event(s), {unmatched} unmatched\n")


if __name__ == "__main__":
    main()
