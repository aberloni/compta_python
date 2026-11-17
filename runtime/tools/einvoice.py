"""
Facturation électronique — turn a bill into a Factur-X file (built here, in
the app) and send it to the SUPER PDP plateforme agréée, which is only used as
the transmission channel (see documentation/facturx.md, "Décision"). Used by
the "Digital" page (view_digital.py, through app_gui.py).

Factur-X = the bill's usual PDF (same HTML as packages/export/htmlFormater.py)
rendered by WeasyPrint as PDF/A-3b, with:
  - factur-x.xml attached (AFRelationship /Data): the CII XML, profile
    EN 16931, built by build_cii() from the same Bill / Project / Client /
    infos values as the PDF, so both stay arithmetically identical
  - the Factur-X XMP metadata (fx: extension schema, profile "EN 16931")
Written to exports/digital/{fullUid}_{client}_{project}_facturx.pdf, plus
the XML next to it.

Pipeline (check_bill / send_bill):
  1. make_facturx() — local, no network
  2. SUPER PDP validation report (/validation_reports) — a check, nothing sent
  3. send_bill() only: POST /invoices if the report is valid, then record it
     in database/digital/superpdp.digital

database/digital/superpdp.digital — invoices sent, one line each, tab-separated:
    fullUid   superpdpId   sentAt(YYYY-MM-DD HH:MM)   statusCode   statusText
The status columns are refreshed from the API by refresh_statuses().
"""

import calendar
import os
import re
from datetime import datetime
from xml.etree.ElementTree import Element, SubElement, register_namespace, tostring

from modules import superpdp
from modules.assocs import Assoc
from modules.path import Path
from packages.database.database import DatabaseType

SENT_FILE = "superpdp.digital"
SENT_HEADER = "# facture\tid SUPER PDP\tenvoyée le\tstatut\tlibellé du statut\n"

EU_COUNTRIES = {"AT", "BE", "BG", "CY", "CZ", "DE", "DK", "EE", "ES", "FI", "FR", "GR", "HR", "HU",
                "IE", "IT", "LT", "LU", "LV", "MT", "NL", "PL", "PT", "RO", "SE", "SI", "SK"}

# French e-invoicing mandatory notes (BR-FR-05)
NOTES = [
    ("PMT", "Indemnité forfaitaire pour frais de recouvrement en cas de retard de paiement : 40 €"),
    ("PMD", "Pénalités de retard : trois fois le taux d'intérêt légal"),
    ("AAB", "Pas d'escompte pour paiement anticipé"),
]

NS = {
    "rsm": "urn:un:unece:uncefact:data:standard:CrossIndustryInvoice:100",
    "ram": "urn:un:unece:uncefact:data:standard:ReusableAggregateBusinessInformationEntity:100",
    "qdt": "urn:un:unece:uncefact:data:standard:QualifiedDataType:100",
    "udt": "urn:un:unece:uncefact:data:standard:UnqualifiedDataType:100",
}
GUIDELINE_EN16931 = "urn:cen.eu:en16931:2017"


class EInvoiceError(Exception):
    pass


# ─── helpers ──────────────────────────────────────────────────────────────────

def _amt(v):
    return f"{round(v + 0.0, 2):.2f}"


def _qty(v):
    return f"{v:.4f}".rstrip("0").rstrip(".")


def _digits(s):
    return re.sub(r"\D", "", s or "")


def _address(raw, country):
    """'street|street 2|93100 MONTREUIL' → {lines, post_code, city, country}
    (last part = post code + city)."""
    parts = [p.strip() for p in (raw or "").split("|") if p.strip()]
    out = {"lines": [], "post_code": "", "city": "", "country": country}
    if not parts:
        return out
    last = parts.pop()
    m = re.match(r"^([A-Z]{0,2}-?\d{4,5})\s+(.+)$", last)
    if m:
        out["post_code"], out["city"] = m.group(1), m.group(2)
    else:
        out["city"] = last
    out["lines"] = parts[:3]
    return out


def _business_process(operation):
    """BT-23 cadre de facturation: S1 services, B1 biens, M1 mixte."""
    op = (operation or "").lower()
    if "service" in op:
        return "S1"
    if "bien" in op:
        return "B1"
    return "M1"


def client_siren(client):
    """Client SIREN from `siren:` or the first 9 digits of `siret:`, '' if none."""
    siren = _digits(client.assoc.filterKey("siren"))
    if not siren:
        siren = _digits(client.assoc.filterKey("siret"))[:9]
    return siren if len(siren) == 9 else ""


def client_eaddress(client):
    """(scheme, value) the invoice is routed to: `eaddress:scheme:value` in the
    client file (e.g. 0208:0123456789 for a Belgian company on Peppol), else
    0225:{SIREN} for a French one (annuaire PPF). None if unknown."""
    raw = (client.assoc.filterKey("eaddress") or "").strip()
    if raw:
        scheme, sep, value = raw.partition(":")
        if sep and scheme.strip() and value.strip():
            return scheme.strip(), value.strip()
    siren = client_siren(client)
    if siren:
        return "0225", siren
    return None


def _vat_category(client, rate):
    """(code, exemption reason) — S taxed; else E (FR), AE (autoliquidation
    UE) or G (hors UE). The reason is the country file's `mention`."""
    if rate > 0:
        return "S", None
    info = client.getCountryInfo()
    mention = info.filterKey("mention") if info else None
    if client.country == "FR":
        return "E", mention or "TVA non applicable"
    if client.country in EU_COUNTRIES:
        return "AE", mention or "Autoliquidation"
    return "G", mention or "Exportation hors UE"


# ─── invoice data (same lines and totals as the PDF) ──────────────────────────

def invoice_data(project, bill):
    """Plain dict of everything the CII needs, checked against the PDF totals."""
    autoe = Assoc("autoe", DatabaseType.infos)
    statics = Assoc("statics", DatabaseType.infos)
    rib = Assoc("rib", DatabaseType.infos)
    client = bill.getClient()
    if client is None:
        raise EInvoiceError("client introuvable pour cette facture")

    fuid = bill.getFullUid()
    if not fuid:
        raise EInvoiceError("identifiant de facture introuvable")

    seller_siren = _digits(autoe.filterKey("siren"))
    if len(seller_siren) != 9:
        raise EInvoiceError("SIREN absent ou invalide dans infos/autoe.info")

    eaddress = client_eaddress(client)
    if eaddress is None:
        raise EInvoiceError(f"adresse électronique du client inconnue : ajouter siren: (ou siret:) "
                            f"ou eaddress: dans clients/{client.uid}.cli")

    rate = bill.getTVA()
    category, exemption = _vat_category(client, rate)
    if bill.hasTransactions() and rate > 0:
        raise EInvoiceError("facture avec frais (+frais) et TVA : non géré en facture électronique")

    # ── lines: same split as the PDF (one per month, or one forfait line) ──
    lines = []

    def add_line(name, qty, unit, price, net, start=None, end=None):
        lines.append({"id": str(len(lines) + 1), "name": name, "qty": qty, "unit": unit,
                      "price": price, "net": round(net, 2), "start": start, "end": end})

    designation = bill.label or "Prestation"
    if bill.isForfait():
        ht = round(bill.getHT(), 2)
        add_line(designation, 1, "C62", ht, ht, bill.start, bill.end)
    elif bill.jours is not None:
        add_line(designation, bill.jours, "DAY", project.getTaux(bill.start), bill.getHT(), bill.start, bill.end)
    else:
        for m in bill.getTimespanMonths():
            days = bill.countDays(m)
            if days <= 0:
                continue
            dt = datetime.strptime(m, "%Y-%m")
            last = dt.replace(day=calendar.monthrange(dt.year, dt.month)[1])
            add_line(f"{designation} {calendar.month_abbr[dt.month]} {dt.year}", days, "DAY",
                     project.getTaux(dt), bill.getHT(m), max(dt, bill.start), min(last, bill.end))
    for t in bill.transactions:
        add_line(f"{t.getType()} : {t.label}", t.quantity, "C62", t.price, t.solvePrice())
    if not lines:
        raise EInvoiceError("facture sans ligne (aucun jour facturé)")

    lines_total = round(sum(l["net"] for l in lines), 2)
    vat_total = round(lines_total * rate, 2)
    ttc = round(lines_total + vat_total, 2)
    if abs(ttc - bill.getTTC()) > 0.011:
        raise EInvoiceError(f"total TTC incohérent ({ttc:.2f} au lieu de {bill.getTTC():.2f} sur le PDF)")

    buyer_siren = client_siren(client)
    return {
        "number": fuid,
        "issue_date": bill.getDatetime(),
        "due_date": datetime.strptime(bill.limit, "%Y-%m-%d"),
        "period": (bill.start, bill.end),
        "process": _business_process(statics.filterKey("operation")),
        "project": (project.uid, bill.objet or project.name),
        "seller": {
            "name": autoe.filterKey("name"),
            "legal_info": statics.filterKey("dispense"),
            "siren": seller_siren,
            "eaddress": ("0225", seller_siren),
            "address": _address(autoe.filterKey("address"), "FR"),
            "vat": (autoe.filterKey("tva") or "").replace(" ", ""),
            "email": autoe.filterKey("email"),
            "phone": autoe.filterKey("phone"),
        },
        "buyer": {
            "name": client.name,
            "siren": buyer_siren,
            "eaddress": eaddress,
            "address": _address(client.address, client.country),
            "vat": (client.tva_number or "").replace(" ", ""),
        },
        "iban": (rib.filterKey("iban") or "").replace(" ", ""),
        "account_name": rib.filterKey("titulaire"),
        "bic": rib.filterKey("bic"),
        "category": category,
        "rate": rate,
        "exemption": exemption,
        "lines": lines,
        "lines_total": lines_total,
        "vat_total": vat_total,
        "ttc": ttc,
    }


# ─── CII XML (Factur-X profile EN 16931) ─────────────────────────────────────

def _el(parent, tag, text=None, **attrs):
    prefix, name = tag.split(":")
    e = SubElement(parent, f"{{{NS[prefix]}}}{name}", attrs)
    if text is not None:
        e.text = str(text)
    return e


def _date(parent, tag, dt):
    _el(_el(parent, tag), "udt:DateTimeString", dt.strftime("%Y%m%d"), format="102")


def _party(parent, tag, p, with_contact=False):
    """CII TradeParty — child order fixed by the XSD."""
    party = _el(parent, tag)
    _el(party, "ram:Name", p["name"])
    if p.get("legal_info"):
        _el(party, "ram:Description", p["legal_info"])
    if p.get("siren"):
        _el(_el(party, "ram:SpecifiedLegalOrganization"), "ram:ID", p["siren"], schemeID="0002")
    if with_contact and (p.get("phone") or p.get("email")):
        contact = _el(party, "ram:DefinedTradeContact")
        if p.get("phone"):
            _el(_el(contact, "ram:TelephoneUniversalCommunication"), "ram:CompleteNumber", p["phone"])
        if p.get("email"):
            _el(_el(contact, "ram:EmailURIUniversalCommunication"), "ram:URIID", p["email"])
    a = p["address"]
    addr = _el(party, "ram:PostalTradeAddress")
    if a["post_code"]:
        _el(addr, "ram:PostcodeCode", a["post_code"])
    for tag_, line in zip(("ram:LineOne", "ram:LineTwo", "ram:LineThree"), a["lines"]):
        _el(addr, tag_, line)
    if a["city"]:
        _el(addr, "ram:CityName", a["city"])
    _el(addr, "ram:CountryID", a["country"])
    _el(_el(party, "ram:URIUniversalCommunication"), "ram:URIID", p["eaddress"][1], schemeID=p["eaddress"][0])
    if p.get("vat"):
        _el(_el(party, "ram:SpecifiedTaxRegistration"), "ram:ID", p["vat"], schemeID="VA")


def build_cii(d):
    """CII XML bytes (factur-x.xml) for invoice_data() `d`."""
    for prefix, uri in NS.items():
        register_namespace(prefix, uri)

    root = Element(f"{{{NS['rsm']}}}CrossIndustryInvoice")

    ctx = _el(root, "rsm:ExchangedDocumentContext")
    _el(_el(ctx, "ram:BusinessProcessSpecifiedDocumentContextParameter"), "ram:ID", d["process"])
    _el(_el(ctx, "ram:GuidelineSpecifiedDocumentContextParameter"), "ram:ID", GUIDELINE_EN16931)

    doc = _el(root, "rsm:ExchangedDocument")
    _el(doc, "ram:ID", d["number"])
    _el(doc, "ram:TypeCode", "380")
    _date(doc, "ram:IssueDateTime", d["issue_date"])
    for code, text in NOTES:
        note = _el(doc, "ram:IncludedNote")
        _el(note, "ram:Content", text)
        _el(note, "ram:SubjectCode", code)

    tx = _el(root, "rsm:SupplyChainTradeTransaction")
    rate_str = _amt(d["rate"] * 100)
    for l in d["lines"]:
        item = _el(tx, "ram:IncludedSupplyChainTradeLineItem")
        _el(_el(item, "ram:AssociatedDocumentLineDocument"), "ram:LineID", l["id"])
        _el(_el(item, "ram:SpecifiedTradeProduct"), "ram:Name", l["name"])
        _el(_el(_el(item, "ram:SpecifiedLineTradeAgreement"), "ram:NetPriceProductTradePrice"),
            "ram:ChargeAmount", _amt(l["price"]))
        _el(_el(item, "ram:SpecifiedLineTradeDelivery"), "ram:BilledQuantity", _qty(l["qty"]), unitCode=l["unit"])
        settle = _el(item, "ram:SpecifiedLineTradeSettlement")
        tax = _el(settle, "ram:ApplicableTradeTax")
        _el(tax, "ram:TypeCode", "VAT")
        _el(tax, "ram:CategoryCode", d["category"])
        _el(tax, "ram:RateApplicablePercent", rate_str)
        if l["start"] and l["end"]:
            period = _el(settle, "ram:BillingSpecifiedPeriod")
            _date(period, "ram:StartDateTime", l["start"])
            _date(period, "ram:EndDateTime", l["end"])
        _el(_el(settle, "ram:SpecifiedTradeSettlementLineMonetarySummation"), "ram:LineTotalAmount", _amt(l["net"]))

    agreement = _el(tx, "ram:ApplicableHeaderTradeAgreement")
    _party(agreement, "ram:SellerTradeParty", d["seller"], with_contact=True)
    _party(agreement, "ram:BuyerTradeParty", d["buyer"])
    project = _el(agreement, "ram:SpecifiedProcuringProject")
    _el(project, "ram:ID", d["project"][0])
    _el(project, "ram:Name", d["project"][1])

    _el(tx, "ram:ApplicableHeaderTradeDelivery")

    settlement = _el(tx, "ram:ApplicableHeaderTradeSettlement")
    _el(settlement, "ram:PaymentReference", d["number"])
    _el(settlement, "ram:InvoiceCurrencyCode", "EUR")
    if d["iban"]:
        means = _el(settlement, "ram:SpecifiedTradeSettlementPaymentMeans")
        _el(means, "ram:TypeCode", "58")  # virement SEPA
        account = _el(means, "ram:PayeePartyCreditorFinancialAccount")
        _el(account, "ram:IBANID", d["iban"])
        if d["account_name"]:
            _el(account, "ram:AccountName", d["account_name"])
        if d["bic"]:
            _el(_el(means, "ram:PayeeSpecifiedCreditorFinancialInstitution"), "ram:BICID", d["bic"])
    tax = _el(settlement, "ram:ApplicableTradeTax")
    _el(tax, "ram:CalculatedAmount", _amt(d["vat_total"]))
    _el(tax, "ram:TypeCode", "VAT")
    if d["exemption"]:
        _el(tax, "ram:ExemptionReason", d["exemption"])
    _el(tax, "ram:BasisAmount", _amt(d["lines_total"]))
    _el(tax, "ram:CategoryCode", d["category"])
    _el(tax, "ram:RateApplicablePercent", rate_str)
    period = _el(settlement, "ram:BillingSpecifiedPeriod")
    _date(period, "ram:StartDateTime", d["period"][0])
    _date(period, "ram:EndDateTime", d["period"][1])
    _date(_el(settlement, "ram:SpecifiedTradePaymentTerms"), "ram:DueDateDateTime", d["due_date"])
    sums = _el(settlement, "ram:SpecifiedTradeSettlementHeaderMonetarySummation")
    _el(sums, "ram:LineTotalAmount", _amt(d["lines_total"]))
    _el(sums, "ram:TaxBasisTotalAmount", _amt(d["lines_total"]))
    _el(sums, "ram:TaxTotalAmount", _amt(d["vat_total"]), currencyID="EUR")
    _el(sums, "ram:GrandTotalAmount", _amt(d["ttc"]))
    _el(sums, "ram:DuePayableAmount", _amt(d["ttc"]))

    return b'<?xml version="1.0" encoding="UTF-8"?>\n' + tostring(root, encoding="utf-8", xml_declaration=False)


# ─── Factur-X PDF (PDF/A-3b + XML + XMP) ─────────────────────────────────────

# Factur-X XMP: the fx: extension schema declaration + its values
XMP_TEMPLATE = """<rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#">
 <rdf:Description rdf:about="" xmlns:pdfaExtension="http://www.aiim.org/pdfa/ns/extension/" xmlns:pdfaSchema="http://www.aiim.org/pdfa/ns/schema#" xmlns:pdfaProperty="http://www.aiim.org/pdfa/ns/property#">
  <pdfaExtension:schemas><rdf:Bag><rdf:li rdf:parseType="Resource">
   <pdfaSchema:schema>Factur-X PDFA Extension Schema</pdfaSchema:schema>
   <pdfaSchema:namespaceURI>urn:factur-x:pdfa:CrossIndustryDocument:invoice:1p0#</pdfaSchema:namespaceURI>
   <pdfaSchema:prefix>fx</pdfaSchema:prefix>
   <pdfaSchema:property><rdf:Seq>
    <rdf:li rdf:parseType="Resource"><pdfaProperty:name>DocumentFileName</pdfaProperty:name><pdfaProperty:valueType>Text</pdfaProperty:valueType><pdfaProperty:category>external</pdfaProperty:category><pdfaProperty:description>The name of the embedded XML document</pdfaProperty:description></rdf:li>
    <rdf:li rdf:parseType="Resource"><pdfaProperty:name>DocumentType</pdfaProperty:name><pdfaProperty:valueType>Text</pdfaProperty:valueType><pdfaProperty:category>external</pdfaProperty:category><pdfaProperty:description>The type of the hybrid document in capital letters, e.g. INVOICE or ORDER</pdfaProperty:description></rdf:li>
    <rdf:li rdf:parseType="Resource"><pdfaProperty:name>Version</pdfaProperty:name><pdfaProperty:valueType>Text</pdfaProperty:valueType><pdfaProperty:category>external</pdfaProperty:category><pdfaProperty:description>The actual version of the standard applying to the embedded XML document</pdfaProperty:description></rdf:li>
    <rdf:li rdf:parseType="Resource"><pdfaProperty:name>ConformanceLevel</pdfaProperty:name><pdfaProperty:valueType>Text</pdfaProperty:valueType><pdfaProperty:category>external</pdfaProperty:category><pdfaProperty:description>The conformance level of the embedded XML document</pdfaProperty:description></rdf:li>
   </rdf:Seq></pdfaSchema:property>
  </rdf:li></rdf:Bag></pdfaExtension:schemas>
 </rdf:Description>
 <rdf:Description rdf:about="" xmlns:fx="urn:factur-x:pdfa:CrossIndustryDocument:invoice:1p0#">
  <fx:DocumentType>INVOICE</fx:DocumentType>
  <fx:DocumentFileName>factur-x.xml</fx:DocumentFileName>
  <fx:Version>1.0</fx:Version>
  <fx:ConformanceLevel>EN 16931</fx:ConformanceLevel>
 </rdf:Description>
</rdf:RDF>
"""


def export_dir():
    return os.path.join(Path.getExportFolderPath(), "digital")


def make_facturx(project, bill):
    """Write the bill's Factur-X PDF (+ its XML) to exports/digital/.
    Returns (fuid, pdf_path). Local only, no network."""
    from weasyprint import HTML, Attachment
    from packages.export.htmlFormater import generateHtml

    d = invoice_data(project, bill)
    xml = build_cii(d)

    os.makedirs(export_dir(), exist_ok=True)
    name = f"{d['number']}_{bill.getClient().uid}_{project.uid}"
    base = os.path.join(export_dir(), name + "_facturx")
    with open(base + ".xml", "wb") as f:
        f.write(xml)
    xmp_path = base + ".xmp"
    with open(xmp_path, "w", encoding="utf-8") as f:
        f.write(XMP_TEMPLATE)

    # same HTML as the regular PDF (generateHtml writes it to exports/billings/)
    html_path = generateHtml(project, bill, name)
    try:
        HTML(html_path).write_pdf(
            base + ".pdf",
            pdf_variant="pdf/a-3b",
            attachments=[Attachment(string=xml, name="factur-x.xml", relationship="Data",
                                    description="Factur-X invoice (EN 16931)")],
            xmp_metadata=[xmp_path],
        )
    finally:
        for path in (html_path, xmp_path):
            if os.path.isfile(path):
                os.remove(path)
    return d["number"], base + ".pdf"


# ─── sent invoices record ─────────────────────────────────────────────────────

def _sent_path():
    return Path.getDbTypePath(DatabaseType.digital) + SENT_FILE


def load_sent():
    """{fullUid: {id, sent_at, status, status_text}} from superpdp.digital."""
    out = {}
    path = _sent_path()
    if not os.path.isfile(path):
        return out
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            if not line.strip() or line.startswith("#"):
                continue
            cols = line.rstrip("\n").split("\t")
            cols += [""] * (5 - len(cols))
            out[cols[0].strip()] = {"id": cols[1].strip(), "sent_at": cols[2].strip(),
                                    "status": cols[3].strip(), "status_text": cols[4].strip()}
    return out


def _write_sent(sent):
    path = _sent_path()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(SENT_HEADER)
        for fuid, s in sent.items():
            f.write("\t".join([fuid, s["id"], s["sent_at"], s["status"], s["status_text"]]) + "\n")


# ─── pipeline (called by app_gui.py) ──────────────────────────────────────────

def _load_bill(project_uid, bill_uid):
    from packages.database.database import Database
    db = Database.init_billing()
    project = db.getProject(project_uid)
    if project is None:
        raise EInvoiceError(f"projet {project_uid} introuvable")
    bill = next((b for b in project.bills if b.uid == bill_uid), None)
    if bill is None:
        raise EInvoiceError(f"facture {bill_uid} introuvable pour ce projet")
    return project, bill


def _guard(fn):
    def wrapper(*args, **kwargs):
        try:
            return fn(*args, **kwargs)
        except (EInvoiceError, superpdp.SuperPdpError) as e:
            return {"ok": False, "error": str(e)}
        except Exception as e:  # network errors, unexpected API answers
            return {"ok": False, "error": f"{type(e).__name__} : {e}"}
    wrapper.__doc__ = fn.__doc__
    return wrapper


def _validate(path):
    with open(path, "rb") as f:
        return superpdp.validate(os.path.basename(path), f.read())


@_guard
def check_connection():
    """Who the credentials belong to, and whether it's the sandbox."""
    if not superpdp.is_configured():
        return {"ok": False, "error": "identifiants manquants : remplir runtime/superpdp.conf"}
    c = superpdp.company_me()
    return {"ok": True, "name": c.get("formal_name") or c.get("trade_name") or "?",
            "number": c.get("number", ""), "env": c.get("env", "")}


@_guard
def check_bill(project_uid, bill_uid):
    """Build the Factur-X and get SUPER PDP's validation report, without
    sending. With no API credentials, only builds it."""
    fuid, path = make_facturx(*_load_bill(project_uid, bill_uid))
    if not superpdp.is_configured():
        return {"ok": True, "fuid": fuid, "path": path, "valid": None,
                "failures": [], "note": "Factur-X généré — validation non faite (identifiants API manquants)"}
    report = _validate(path)
    return {"ok": True, "fuid": fuid, "path": path, "valid": bool(report.get("is_valid")),
            "failures": superpdp.failures(report)}


@_guard
def send_bill(project_uid, bill_uid):
    """Build, validate, then send one bill. Refuses a bill already sent, or
    one whose validation report isn't valid."""
    project, bill = _load_bill(project_uid, bill_uid)
    sent = load_sent()
    if bill.getFullUid() in sent:
        return {"ok": False, "error": f"déjà envoyée (id SUPER PDP {sent[bill.getFullUid()]['id']})"}

    fuid, path = make_facturx(project, bill)
    report = _validate(path)
    if not report.get("is_valid"):
        return {"ok": False, "error": "validation refusée — rien n'a été envoyé",
                "failures": superpdp.failures(report), "path": path}

    with open(path, "rb") as f:
        invoice = superpdp.send_invoice(f.read(), fuid)
    status, text = superpdp.last_status(invoice)
    sent = load_sent()
    sent[fuid] = {"id": str(invoice["id"]), "sent_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
                  "status": status or "api:uploaded", "status_text": text}
    _write_sent(sent)
    return {"ok": True, "fuid": fuid, "id": invoice["id"], "status": sent[fuid]["status"],
            "status_text": text, "path": path}


@_guard
def refresh_statuses():
    """Fetch the latest status of every recorded invoice from the API."""
    sent = load_sent()
    errors = []
    for fuid, s in sent.items():
        try:
            status, text = superpdp.last_status(superpdp.get_invoice(s["id"]))
        except Exception as e:
            errors.append(f"{fuid} : {e}")
            continue
        if status:
            s["status"], s["status_text"] = status, text
    if sent:
        _write_sent(sent)
    return {"ok": True, "count": len(sent), "errors": errors}
