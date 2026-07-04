"""
pdf_to_csv.py
Extrait les transactions de tous les PDFs dans database/releves/ → CSV

Usage:
    python runtime/pdf_to_csv.py

Un CSV par PDF, généré dans database/releves/
"""

import sys
import csv
import re
from pathlib import Path

try:
    import pdfplumber
except ImportError:
    sys.exit("Dépendance manquante : pip install pdfplumber --break-system-packages")


# ---------------------------------------------------------------------------
# Patterns de détection
# ---------------------------------------------------------------------------

# Date au format DD/MM/YYYY ou DD/MM/YY
DATE_RE = re.compile(r"\b(\d{2}/\d{2}/(?:\d{4}|\d{2}))\b")

# Montant : 1 234,56 ou 1234.56 ou -1 234,56
AMOUNT_RE = re.compile(r"-?\s*\d[\d\s]*[.,]\d{2}")


def clean_amount(raw: str) -> float:
    """Convertit une string montant en float (gère espaces et virgules)."""
    s = raw.strip().replace(" ", "").replace("\xa0", "").replace(",", ".")
    return float(s)


def is_amount(token: str) -> bool:
    return bool(AMOUNT_RE.fullmatch(token.strip()))


# ---------------------------------------------------------------------------
# Extraction principale
# ---------------------------------------------------------------------------

def extract_transactions(pdf_path: str) -> list[dict]:
    transactions = []

    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            # 1) Essai via tables structurées
            tables = page.extract_tables()
            for table in tables:
                for row in table:
                    if not row:
                        continue
                    tx = parse_row(row)
                    if tx:
                        transactions.append(tx)

            # 2) Fallback : texte ligne par ligne
            if not transactions:
                text = page.extract_text()
                if text:
                    for line in text.splitlines():
                        tx = parse_line(line)
                        if tx:
                            transactions.append(tx)

    return transactions


def parse_row(row: list) -> dict | None:
    """Tente d'extraire date / libellé / débit / crédit depuis une ligne de tableau."""
    cells = [str(c).strip() if c else "" for c in row]

    date = None
    label_parts = []
    amounts = []

    for cell in cells:
        if not cell:
            continue
        if not date and DATE_RE.search(cell):
            date = DATE_RE.search(cell).group(1)
            # reste du cell après la date = début du libellé
            rest = DATE_RE.sub("", cell).strip()
            if rest:
                label_parts.append(rest)
        elif is_amount(cell):
            amounts.append(clean_amount(cell))
        else:
            label_parts.append(cell)

    if not date or not amounts:
        return None

    label = " ".join(p for p in label_parts if p)
    debit = credit = ""

    if len(amounts) == 1:
        val = amounts[0]
        if val < 0:
            debit = abs(val)
        else:
            credit = val
    elif len(amounts) >= 2:
        debit = amounts[0] if amounts[0] != 0 else ""
        credit = amounts[1] if amounts[1] != 0 else ""

    return {"date": date, "libelle": label, "debit": debit, "credit": credit}


def parse_line(line: str) -> dict | None:
    """Fallback texte brut : cherche date + montants dans la ligne."""
    m = DATE_RE.search(line)
    if not m:
        return None

    date = m.group(1)
    after_date = line[m.end():].strip()

    # chercher tous les montants dans la suite
    amounts_raw = AMOUNT_RE.findall(after_date)
    if not amounts_raw:
        return None

    amounts = []
    for a in amounts_raw:
        try:
            amounts.append(clean_amount(a))
        except ValueError:
            pass

    # libellé = texte entre date et premier montant
    first_amount_pos = AMOUNT_RE.search(after_date)
    label = after_date[:first_amount_pos.start()].strip() if first_amount_pos else after_date

    debit = credit = ""
    if len(amounts) == 1:
        val = amounts[0]
        if val < 0:
            debit = abs(val)
        else:
            credit = val
    elif len(amounts) >= 2:
        debit = amounts[0] if amounts[0] != 0 else ""
        credit = amounts[1] if amounts[1] != 0 else ""

    return {"date": date, "libelle": label, "debit": debit, "credit": credit}


# ---------------------------------------------------------------------------
# Export CSV
# ---------------------------------------------------------------------------

def to_csv(transactions: list[dict], output_path: str):
    with open(output_path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=["date", "libelle", "debit", "credit"], delimiter=";")
        writer.writeheader()
        writer.writerows(transactions)
    print(f"{len(transactions)} transaction(s) exportée(s) → {output_path}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

RELEVES_DIR = Path(__file__).parent.parent / "database" / "releves"

if __name__ == "__main__":
    if not RELEVES_DIR.exists():
        RELEVES_DIR.mkdir()
        print(f"Dossier créé : {RELEVES_DIR}")
        print("Place tes PDFs dans ce dossier puis relance le script.")
        sys.exit(0)

    pdfs = sorted(RELEVES_DIR.glob("*.pdf"))
    if not pdfs:
        print(f"Aucun PDF trouvé dans {RELEVES_DIR}")
        sys.exit(0)

    for pdf_path in pdfs:
        csv_path = pdf_path.with_suffix(".csv")
        print(f"\nLecture : {pdf_path.name}")
        txs = extract_transactions(str(pdf_path))
        if not txs:
            print("  → Aucune transaction détectée.")
        else:
            to_csv(txs, str(csv_path))
