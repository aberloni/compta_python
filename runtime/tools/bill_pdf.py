"""
Generate a single bill's PDF on demand -- used by the "Éditer les factures"
page's per-row "PDF" button (see app_gui.py: generate_bill_pdf()).
"""

import os

import configs
from packages.database.database import Database
from packages.export.exporter import exportBill
from modules.path import Path


def generate_bill_pdf(project_uid, bill_uid):
    db = Database.init_billing()

    project = db.getProject(project_uid)
    if project is None:
        return {"ok": False, "error": f"projet {project_uid} introuvable"}

    bill = next((b for b in project.bills if b.uid == bill_uid), None)
    if bill is None:
        return {"ok": False, "error": f"facture {bill_uid} introuvable pour ce projet"}

    fuid = bill.getFullUid()
    if fuid is None:
        return {"ok": False, "error": "impossible de calculer l'identifiant de la facture"}

    # this is an explicit on-demand request: always produce the PDF,
    # regardless of the "creatPdf" setting used by full billing runs
    previous_creatPdf = configs.creatPdf
    configs.creatPdf = True
    try:
        exportBill(project, bill)
    finally:
        configs.creatPdf = previous_creatPdf

    pdf_path = os.path.join(
        Path.getExportBillingPath(), f"{fuid}_{bill.getClient().uid}_{project.uid}.pdf"
    )
    if not os.path.isfile(pdf_path):
        return {"ok": False, "error": "le PDF n'a pas été généré"}

    return {"ok": True, "path": pdf_path}
