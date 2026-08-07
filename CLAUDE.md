# CLAUDE.md — compta_python

Headless Python billing tool for a French freelancer (auto-entrepreneur).

Data lives in `database/` at the repo root, but is gitignored — never committed. No personal data goes into git history.
All database files are plain text — quick to write, human-readable.
Backups are manual, via `do_zip_backup.py` (zips `database/` on demand).

---

## Architecture

Personal data lives in `database/` at the repo root (sibling of `runtime/`). It is listed in `.gitignore` so it never enters git history — backup is manual (zip), not git sync. `modules/path.py → Path.getDbPath()` resolves it via `configs.dbPath` (repo root).

```
database/
  infos/        ← autoe.compta, rib.compta
  clients/      ← {uid}.compta
  projects/     ← {uid}.compta
  tasks/        ← tasks_{YYYY-MM}.compta
  bills/        ← bills_{projectUid}.compta
  wiring/       ← {*}.wire — received bank transfers, matched to bills
  releves/      ← bank statement exports
exports/
  billings/     ← generated HTML, PDF, .dump
  view/         ← generated dashboards (billing.html, wiring.html, tva.html, ...)
```

Repo contains `runtime/` code plus `database/` (gitignored, real data) and `exports/` (generated). `__samples/` has anonymised example `.compta` files.

---

## Data format — `.compta` files

Plain-text, parsed by `modules/assocs.py → Assoc / AssocEntry`.

Syntax: `key:value` or `key:value,value2,value3`

Each file type lives in its own `database/{type}/` subfolder (matched by `DatabaseType` enum).

### infos/autoe.compta
```
name:André BERLEMONT
job:Développeur indépendant
address:12-14 rue Jean-Jacques Rousseau|93100 MONTREUIL
siren:523989440
tva:FR9523989440
email:...
phone:...
```
`|` in address = line break in HTML output.

### infos/rib.compta
```
titulaire:M. André Berlemont
bank:Société Générale
iban:FR76 ...
bic:SOGEFRPP
```

### infos/statics.info
```
dispense:Dispensé d'immatriculation au registre du commerce et des sociétés (RCS) et au répertoire des métiers (RM)
operation:Prestation de services   ← nature de l'opération (facturation électronique / Factur-X, voir documentation/facturx.md) — pas encore affiché sur le PDF
```

### infos/{ISO}.info — per-country TVA rate + invoice mention
```
tva:0.2                          ← TVA rate applied on bills for clients of this country
mention:Autoliquidation - TVA due par le preneur, art. 44 Directive 2006/112/CE
```
Filename = ISO 3166-1 alpha-2 country code (`FR.info`, `BE.info`, ...) — not a language code (`EN` is invalid, UK is `GB`).
`Client.country` (from `clients/{uid}.compta`, defaults to `FR` if absent) selects which file applies.
`Bill.getTVA()` uses this file's `tva` if the client's country file exists and defines it. Otherwise: `FR` clients fall back to the project's own `tva:` field (rétrocompatibilité); non-`FR` clients default to `0` (no French TVA — intracommunautaire/hors UE by default, no need to set `tva:` in non-FR country files unless a rate genuinely applies).
`mention` (optional) is rendered on the bill as `{{mention_block}}`, distinct from the fixed `{{dispense}}` notice (RCS/RM registration exemption, always shown regardless of country).

### clients/{uid}.compta
```
uid:darjeeling
name:Darjeeling production
address:...|...
creditor:DARJEELING SARL
country:BE              ← ISO 3166-1 alpha-2, optional, defaults to FR
tva:BE1006963829        ← client's own VAT number, optional — shown on the bill if present
```
`creditor` = label used to match bank statement lines.

### projects/{uid}.compta
```
uid:merlies
name:The Merlies
client:darjeeling        ← must match a client uid
tva:0.2
taux:280                 ← daily rate € (base, always applicable)
taux:2024-06-01=320      ← rate effective from that date (multiple lines allowed)
taux:2025-01-01=350      ← most recent line <= bill date wins
```
Multiple `taux` lines can coexist. `Project.getTaux(date)` returns the applicable rate at a given date.
If a bill spans months with different rates, `getHT()` sums per-month; the PDF displays `"280 → 320 € HT"`.
Rétrocompatibilité : une seule ligne `taux:280` fonctionne comme avant.
Effective dates (`taux:` and `client:`) accept `YYYY-MM-DD`, `YYYY-MM` (→ 1st of month) or `YYYY` (→ Jan 1), parsed by `modules.system.parseFlexibleDate()`.

Same pattern applies to `client`:
```
client:darjeeling              ← base client (rétrocompat)
client:2025-06-01=autreclient  ← client effective from that date
```
`Project.getClient(date)` returns the Client applicable at that date. `Bill.getClient()` calls it with `bill.start`.
The PDF header uses `bill.getClient()` so the correct client appears per billing period.

### tasks/tasks_{YYYY-MM}.compta
```
# YYYY-MM

projectUid:YYYY-MM-DD
projectUid:YYYY-MM-DD,0.5       ← half day (also: 1/2, 0.25, 0.75, 1/4)
projectUid:YYYY-MM-DD,0         ← zero
projectUid:YYYY-MM-DD,>YYYY-MM  ← redirect: bill to a different month
projectUid:YYYY-MM-DD,"some label"
off:YYYY-MM-DD                  ← vacation / off day, planned (never billed, shown in calendar)
off:YYYY-MM-DD,0.5              ← half-day off
chome:YYYY-MM-DD                ← unaccounted day, no info (never billed, shown in calendar)
chome:YYYY-MM-DD,0.5            ← half-day chômé
```
Time value is a float in [0, 1] representing fraction of an 8h day.

`off` and `chome` are reserved uids for non-billable days. `off` = planned/anticipated time off; `chome` = day with no recorded information. Both are excluded from all billing and project totals, and both appear in `view_tasks_calendar.py` (off in blue, chômé in grey).

**Amélioration prévue** : le `YYYY-MM` dans chaque date est redondant avec le nom de fichier. Cible : accepter juste le jour — `projectUid:DD` ou `projectUid:DD,0.5` — et reconstruire la date complète depuis le nom de fichier dans `Task.__init__`. Rétrocompatibilité avec `YYYY-MM-DD` à conserver.

### bills/bills_{projectUid}.compta
```
YYYY-MM-DD:YYYY-MM-DD,YYYY-MM-DD      ← bill date : period start, period end
YYYY-MM-DD:YYYY-MM-DD,YYYY-MM-DD|280  ← forfait override (fixed amount)
YYYY-MM-DD:YYYY-MM,YYYY-MM            ← day can be omitted: start → 1st of month, end → last day of month
label:Custom prestation label
designation:Subtitle text
frais:Description,150,2               ← additional line: label, unit price, qty
```
Multiple bills per file, one block per bill date. Period start/end accept `YYYY-MM-DD`, `YYYY-MM` (→ 1st/last day of month), or `YYYY` (→ Jan 1/Dec 31). The bill date itself (before the `:`) still requires the full `YYYY-MM-DD`.

---

## Bill UID

Generated by `Bill.solveFullUid()`:

```
{YYYY-MM}_s{week_number}-{index_within_week}
```

Example: `2026-03_s11-01`

Index is 1-based, zero-padded (`01`, `02`, ...).
Week number = Python `strftime("%W")` (Monday-based, 0-padded).

Export filename: `{fullUID}_{clientUid}_{projectUid}.{ext}`

---

## Entry points

| Script | Purpose |
|--------|---------|
| `main_billing.py` | Generate PDFs for a date range (set in `configs.py`) |
| `main_tva.py` | Print HT/TVA/TTC totals per bill |
| `main_unpaid.py` | Cross-reference bills vs bank statements |
| `main_workdays.py` | Count worked/missing days per month |
| `main_labels.py` | View data from bank statements |

Run from `runtime/` directory.

---

## Key classes

| Class | File | Role |
|-------|------|------|
| `Database` | `packages/database/database.py` | Singleton loader; call `Database.init_billing()` or `Database.init_all()` |
| `Assoc` | `modules/assocs.py` | Parses a `.compta` file into `AssocEntry[]` |
| `Project` | `packages/database/project.py` | Holds bills, tasks, client ref, daily rate |
| `Bill` | `packages/database/bill.py` | Date range + tasks slice + totals (HT/TVA/TTC) |
| `Task` | `packages/database/task.py` | One work-day entry (project, date, fraction) |
| `Client` | `packages/database/client.py` | Client info, creditor label |
| `Creditor` | `packages/database/creditor.py` | Freelancer's own info |
| `Exporter` | `packages/export/exporter.py` | Orchestrates HTML + PDF export via WeasyPrint |
| `HtmlFormater` | `packages/export/htmlFormater.py` | Builds the invoice HTML string |
| `Path` | `modules/path.py` | Resolves all paths under `database/` (repo root, gitignored) |

---

## Export pipeline

`main_billing.py` → `exportBills(project, range)` → `exportBill(project, bill)`:
1. Resolve `bill.getFullUid()`
2. `generateHtml()` → writes `.html` to `exports/billings/`
3. `HTML(path).write_pdf()` via **WeasyPrint** → writes `.pdf`

CSS is embedded inline from `runtime/css.css`. **Single-page layout — all bills must fit on one page.**

Each bill also generates a `.dump` file (when debugging) containing a markdown summary with: invoice metadata, client/project details, line items per day, and HT/TVA/TTC totals. See `specs/bills_dump.md` for the expected output format.

### PDF content structure (top → bottom)
1. Freelancer name, job title, SIREN, N°TVA, address
2. Client name + address
3. Invoice ID + object (project name)
4. Line items: one row per month — `month year | Prestation x {days} j | {ht} € HT`
5. Totals block: taux journalier, Total HT, TVA (%), Total TTC
6. Invoice date + payment deadline (30 days)
7. Dispense de TVA notice
8. RIB: titulaire, banque, IBAN, BIC

---

## configs.py

```python
dbExtension = ".compta"
billingRange = ["2026-01", "2026-03"]   # [start, end] inclusive
creatPdf = True
openBillingFolder = True                 # os.startfile() after export (Windows)
```

---

## Conventions

- No external DB. No ORM. No framework.
- `DatabaseType` enum values match subfolder names under `database/`.
- `Assoc.has(name, dbType)` to check file existence before loading.
- `Database.instance` is set on construction — used as a global singleton.
- `Bill.verbose`, `Project.verbose`, `Task.verbose` flags for debug prints.
- `configs.is_debugging()` detects debugger attach (writes `.dump` files).
- `change.log` at repo root tracks every change (code or data), grouped by day (`## YYYY-MM-DD` heading, one bullet per change). Append to it whenever a change is made — don't wait to be asked. Write each bullet as a simple, plain-language sentence describing the task achieved (no file names, function names, or technical detail) — readable by a non-technical person.
