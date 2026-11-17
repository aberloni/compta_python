"""
Client for the SUPER PDP API (plateforme agréée, facturation électronique).
Only used to transmit the Factur-X files the app builds itself
(tools/einvoice.py), check them, and follow their status.

API reference: https://www.superpdp.tech/openapi/ (spec served at
https://api.superpdp.tech/openapi/superpdp.json). All routes are under
/v1.beta and authenticated with an OAuth2 bearer token obtained with the
client credentials flow (client_id / client_secret = the company's own API
key, created in the SUPER PDP dashboard). Sandbox vs production is decided by
the credentials themselves (a sandbox company's key only reaches the sandbox).

Credentials live in runtime/superpdp.conf (gitignored, outside database/ so
they never end up in backup zips):
    client_id:...
    client_secret:...
"""

import json
import os
import time

import requests

API_URL = "https://api.superpdp.tech"
CONF_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "superpdp.conf")
CONF_TEMPLATE = (
    "# Identifiants API SUPER PDP (https://www.superpdp.tech) — fichier local, jamais commité.\n"
    "# À créer dans le tableau de bord SUPER PDP (clé API = client credentials).\n"
    "client_id:\n"
    "client_secret:\n"
)
TIMEOUT = 60

_token = {"value": None, "expires": 0.0}


class SuperPdpError(Exception):
    pass


# ─── config ───────────────────────────────────────────────────────────────────

def load_conf():
    conf = {}
    if not os.path.isfile(CONF_PATH):
        return conf
    with open(CONF_PATH, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            key, sep, value = line.partition(":")
            if sep:
                conf[key.strip()] = value.strip()
    return conf


def is_configured():
    conf = load_conf()
    return bool(conf.get("client_id") and conf.get("client_secret"))


def ensure_conf_file():
    """Create superpdp.conf with empty keys if missing, return its path."""
    if not os.path.isfile(CONF_PATH):
        with open(CONF_PATH, "w", encoding="utf-8") as f:
            f.write(CONF_TEMPLATE)
    return CONF_PATH


# ─── http ─────────────────────────────────────────────────────────────────────

def _error_text(resp):
    try:
        data = resp.json()
        msg = data.get("message") or data.get("error_description") or data.get("error") or json.dumps(data)
    except ValueError:
        msg = resp.text.strip()[:300] or resp.reason
    return f"HTTP {resp.status_code} — {msg}"


def _get_token():
    if _token["value"] and time.time() < _token["expires"] - 30:
        return _token["value"]
    conf = load_conf()
    if not (conf.get("client_id") and conf.get("client_secret")):
        raise SuperPdpError("identifiants SUPER PDP manquants (runtime/superpdp.conf)")
    resp = requests.post(f"{API_URL}/oauth2/token", data={
        "grant_type": "client_credentials",
        "client_id": conf["client_id"],
        "client_secret": conf["client_secret"],
    }, timeout=TIMEOUT)
    if resp.status_code != 200:
        raise SuperPdpError("authentification refusée : " + _error_text(resp))
    data = resp.json()
    _token["value"] = data["access_token"]
    _token["expires"] = time.time() + float(data.get("expires_in", 3600))
    return _token["value"]


def _request(method, path, **kwargs):
    headers = kwargs.pop("headers", {})
    headers["Authorization"] = "Bearer " + _get_token()
    resp = requests.request(method, API_URL + path, headers=headers, timeout=TIMEOUT, **kwargs)
    if resp.status_code == 401:
        _token["value"] = None  # expired / revoked: one retry with a fresh token
        headers["Authorization"] = "Bearer " + _get_token()
        resp = requests.request(method, API_URL + path, headers=headers, timeout=TIMEOUT, **kwargs)
    if resp.status_code >= 400:
        raise SuperPdpError(_error_text(resp))
    return resp


# ─── endpoints ────────────────────────────────────────────────────────────────

def company_me():
    """GET /v1.beta/companies/me — the company the credentials belong to
    (formal_name, number, env = sandbox | production, ...)."""
    return _request("GET", "/v1.beta/companies/me").json()


def validate(file_name, file_bytes):
    """POST /v1.beta/validation_reports — schematron / business rule checks,
    nothing is sent. Returns the report of that one file
    ({is_valid, format, subreports: [{validator, failures, messages}], ...})."""
    files = {"file_name": (file_name, file_bytes, "application/pdf")}
    data = _request("POST", "/v1.beta/validation_reports", files=files).json()
    reports = data.get("data") or []
    if not reports:
        raise SuperPdpError("rapport de validation vide")
    return reports[0]


def send_invoice(pdf_bytes, external_id):
    """POST /v1.beta/invoices — queue a Factur-X PDF for sending. Returns the
    created invoice ({id, events, ...}); delivery itself is asynchronous."""
    resp = _request("POST", "/v1.beta/invoices", params={"external_id": external_id},
                    data=pdf_bytes, headers={"Content-Type": "application/pdf"})
    return resp.json()


def get_invoice(invoice_id):
    """GET /v1.beta/invoices/{id} — invoice with its events (statuses)."""
    return _request("GET", f"/v1.beta/invoices/{int(invoice_id)}").json()


def last_status(invoice):
    """(status_code, status_text) of the most recent event, or ("", "")."""
    events = sorted(invoice.get("events") or [], key=lambda e: (e.get("created_at") or "", e.get("id") or 0))
    if not events:
        return "", ""
    return events[-1].get("status_code", ""), events[-1].get("status_text", "")


def failures(report):
    """Flat list of failure messages of a validation report."""
    out = []
    for sub in report.get("subreports") or []:
        for f in sub.get("failures") or []:
            msg = f.get("message") or f.get("raw") or ""
            if f.get("location"):
                msg += f" ({f['location']})"
            out.append(msg)
    if report.get("error"):
        out.append(report["error"])
    return out
