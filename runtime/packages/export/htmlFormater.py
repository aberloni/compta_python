from datetime import datetime
import calendar
import os

from modules.assocs import Assoc
from modules.path import Path
from packages.database.database import Database, DatabaseType

# ─── template & CSS ───────────────────────────────────────────────────────────

def _load_template():
    path = os.path.join(os.path.dirname(__file__), "..", "..", "bill_template.html")
    with open(os.path.normpath(path), "r", encoding="utf-8") as f:
        return f.read()

def _load_css():
    path = os.path.join(os.path.dirname(__file__), "..", "..", "bill_css.css")
    with open(os.path.normpath(path), "r", encoding="utf-8") as f:
        return f.read()

# ─── line item builders ───────────────────────────────────────────────────────

def _line_days(date, days, ht):
    return (f'<div id="tasks-lines">'
            f'<span class="task-date task-value">{date}</span>'
            f'<span class="task-designation task-value">Prestation x {days:g} j</span>'
            f'<span class="task-price task-value">{ht:.2f} € HT</span>'
            f'</div>')

def _line_label(date, ht, label):
    return (f'<div id="tasks-lines">'
            f'<span class="task-date task-value">{date}</span>'
            f'<span class="task-label task-value">{label}</span>'
            f'<span class="task-price task-value">{ht:.2f} € HT</span>'
            f'</div>')

def _line_transaction(type_, label, qty, price):
    return (f'<div id="tasks-lines">'
            f'<span class="task-date"></span>'
            f'<span class="task-designation">{type_} : {label} x {qty:g}</span>'
            f'<span class="task-price">{price:.2f} € TTC</span>'
            f'</div>')

# ─── main entry point ─────────────────────────────────────────────────────────

def generateHtml(project, bill, exportFileName):

    autoe  = Assoc("autoe",   DatabaseType.infos)
    statics = Assoc("statics", DatabaseType.infos)
    rib    = Assoc("rib",     DatabaseType.infos)
    client = bill.getClient()

    # ── line items ────────────────────────────────────────────────────────────
    line_items = ""

    if bill.isForfait():
        ht   = bill.getHT()
        date = bill.getLabelDate()
        if bill.label:
            line_items += _line_label(date, ht, bill.label)
        else:
            line_items += _line_days(date, bill.countDays(), ht)
    else:
        months = bill.getTimespanMonths()
        if not months:
            exit("issue: need month")
        for m in months:
            cnt = bill.countDays(m)
            if cnt <= 0:
                continue
            ht  = bill.getHT(m)
            dt  = datetime.strptime(m, "%Y-%m")
            lbl = calendar.month_abbr[dt.month] + " " + str(dt.year)
            if bill.label:
                line_items += _line_label(lbl, ht, bill.label)
            else:
                line_items += _line_days(lbl, cnt, ht)

    if bill.hasTransactions():
        for t in bill.transactions:
            line_items += _line_transaction(t.getType(), t.label, t.quantity, t.solvePrice())

    # ── totals ────────────────────────────────────────────────────────────────
    ht      = bill.getHT()
    tva     = bill.getTVA()
    abs_tva = bill.getTvaTotal()
    ttc     = bill.getTTC()
    perc    = f"{tva * 100:g}%"

    _taux_range = project.getTauxRange(bill.start, bill.end)
    if len(_taux_range) > 1:
        taux_str = " → ".join(f"{t:.2f}" for t in _taux_range)
    else:
        taux_str = f"{_taux_range[0] if _taux_range else project.getTaux():.2f}"

    tva_block = ""
    if tva > 0:
        tva_block = (f'<div id="tva"><span id="tva-label" class="assocLabel">TVA ({perc})</span>'
                     f'<span id="tva-value" class="assocValue">'
                     f'<span class="amount">{abs_tva:.2f}</span><span class="currency">€</span><span class="unit"></span>'
                     f'</span></div>')

    frais_block = ""
    if bill.hasTransactions():
        frais_tot = bill.getTransactionsTTC()
        frais_block = (f'<div id="frais">'
                       f'<span id="frais-label" class="assocLabel">Total Frais</span>'
                       f'<span id="frais-value" class="assocValue">'
                       f'<span class="amount">{frais_tot:.2f}</span><span class="currency">€</span><span class="unit">TTC</span>'
                       f'</span></div>')

    designation_block = ""
    if bill.designation:
        designation_block = f'<div id="bill-designation">{bill.designation}</div>'

    mention_block = ""
    country_info = client.getCountryInfo()
    if country_info:
        mention = country_info.filterKey("mention")
        if mention:
            mention_block = f'<div id="country-mention" class="mention">{mention}</div>'

    # ── fill template ─────────────────────────────────────────────────────────
    html = _load_template()
    html = html.replace("{{css}}",               _load_css())
    html = html.replace("{{title}}",             exportFileName)
    html = html.replace("{{autoe_name}}",        autoe.filterKey("name"))
    html = html.replace("{{autoe_job}}",         autoe.filterKey("job"))
    html = html.replace("{{siren}}",             autoe.filterKey("siren"))
    html = html.replace("{{tva_num}}",           autoe.filterKey("tva"))
    html = html.replace("{{address}}",           autoe.filterHtmlValue("address"))
    html = html.replace("{{client_name}}",       client.name)
    client_address = client.assoc.filterHtmlValue("address")
    if client.country != "FR":
        client_address += f" ({client.country})"
    if client.tva_number:
        client_address += f"<br/>TVA : {client.tva_number}"
    html = html.replace("{{client_address}}",    client_address)
    html = html.replace("{{bill_uid}}",          bill.getFullUid())
    html = html.replace("{{project_name}}",      project.name)
    html = html.replace("{{designation_block}}", designation_block)
    html = html.replace("{{mention_block}}",     mention_block)
    html = html.replace("{{line_items}}",        line_items)
    html = html.replace("{{taux}}",              taux_str)
    html = html.replace("{{total_ht}}",          f"{ht:.2f}")
    html = html.replace("{{tva_block}}",         tva_block)
    html = html.replace("{{frais_block}}",       frais_block)
    html = html.replace("{{total_ttc}}",         f"{ttc:.2f}")
    html = html.replace("{{bill_date}}",         str(bill.uid))
    html = html.replace("{{bill_limit}}",        str(bill.limit))
    html = html.replace("{{dispense}}",          statics.filterKey("dispense"))
    html = html.replace("{{operation}}",         statics.filterKey("operation"))
    html = html.replace("{{rib_titulaire}}",     rib.filterKey("titulaire"))
    html = html.replace("{{rib_bank}}",          rib.filterHtmlValue("bank"))
    html = html.replace("{{rib_iban}}",          rib.filterKey("iban"))
    html = html.replace("{{rib_bic}}",           rib.filterKey("bic"))
    html = html.replace("{{email}}",             autoe.filterKey("email"))
    html = html.replace("{{phone}}",             autoe.filterKey("phone"))

    # ── write ─────────────────────────────────────────────────────────────────
    export_path = Database.folderExportBilling() + exportFileName + ".html"
    with open(export_path, "w", encoding="utf-8") as f:
        f.write(html)

    print("     generated HTML : " + exportFileName)
    return export_path
