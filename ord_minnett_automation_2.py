"""
Ord Minnett Email Automation
==============================
Scans a shared Outlook inbox for Ord Minnett emails, downloads PDF attachments,
extracts key fields from the PDF, renames the file, saves to desktop folder,
and archives the email.

Setup (one time):
    pip install pypdf msal requests

Output folder:
    Files saved to ~/Desktop/Ord Minnett Receipts/
    Filename format: DDMMYYYY ClientName Platform AccountNumber CompanyName TransactionType.pdf
    e.g. 10032026 Smith Family Super Panorama 123456 BHP Group Limited Bought.pdf
"""

import re
import base64
import requests
import msal
from pathlib import Path
from pypdf import PdfReader
from datetime import datetime
import io

# ── CONFIG ───────────────────────────────────────────────────────────────────

TENANT_ID          = "YOUR_TENANT_ID"
CLIENT_ID          = "YOUR_CLIENT_ID"
CLIENT_SECRET      = "YOUR_CLIENT_SECRET"
SHARED_MAILBOX     = "YOUR_SHARED_MAILBOX"
ORD_MINNETT_SENDER = "ORDMINNET or other Broker email"

FILTER_BY_SENDER   = True   # set to False to process ALL emails in shared inbox

OUTPUT_FOLDER  = Path.home() / "Desktop" / "Ord Minnett Receipts"
LOG_FILE       = Path("ord_minnett_log.txt")

# ── AUTH ──────────────────────────────────────────────────────────────────────

def get_access_token() -> str:
    authority = f"https://login.microsoftonline.com/{TENANT_ID}"
    app = msal.ConfidentialClientApplication(
        CLIENT_ID,
        authority=authority,
        client_credential=CLIENT_SECRET
    )
    result = app.acquire_token_for_client(
        scopes=["https://graph.microsoft.com/.default"]
    )
    if "access_token" not in result:
        raise Exception(f"Auth failed: {result.get('error_description')}")
    return result["access_token"]


# ── GRAPH API HELPERS ─────────────────────────────────────────────────────────

def get_inbox_messages(token: str) -> list[dict]:
    """Fetch emails from the shared inbox — filtered by sender or all, based on config."""
    base = (
        f"https://graph.microsoft.com/v1.0/users/{SHARED_MAILBOX}"
        f"/mailFolders/inbox/messages"
    )
    if FILTER_BY_SENDER:
        query = f"?$filter=from/emailAddress/address eq '{ORD_MINNETT_SENDER}'&$top=100"
    else:
        query = "?$top=100"

    url = base + query + "&$select=id,subject,from,receivedDateTime,hasAttachments"
    headers = {"Authorization": f"Bearer {token}"}
    messages = []

    while url:
        resp = requests.get(url, headers=headers)
        resp.raise_for_status()
        data = resp.json()
        messages.extend(data.get("value", []))
        url = data.get("@odata.nextLink")

    return messages


def get_attachments(token: str, message_id: str) -> list[dict]:
    """Get all attachments for a given message."""
    url = (
        f"https://graph.microsoft.com/v1.0/users/{SHARED_MAILBOX}"
        f"/messages/{message_id}/attachments"
    )
    resp = requests.get(url, headers={"Authorization": f"Bearer {token}"})
    resp.raise_for_status()
    return resp.json().get("value", [])


def archive_email(token: str, message_id: str):
    """Move email to the Archive folder."""
    url = f"https://graph.microsoft.com/v1.0/users/{SHARED_MAILBOX}/mailFolders/archive"
    resp = requests.get(url, headers={"Authorization": f"Bearer {token}"})
    resp.raise_for_status()
    archive_id = resp.json()["id"]

    move_url = (
        f"https://graph.microsoft.com/v1.0/users/{SHARED_MAILBOX}"
        f"/messages/{message_id}/move"
    )
    resp = requests.post(
        move_url,
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        json={"destinationId": archive_id}
    )
    resp.raise_for_status()


# ── PDF EXTRACTION ────────────────────────────────────────────────────────────

def extract_pdf_fields(pdf_bytes: bytes) -> dict:
    """
    Extract key fields from an Ord Minnett confirmation PDF.

    Expected PDF format:
        Confirmation Date: DD/MM/YYYY
        Client Name
        [next line] Platform  AccountNumber
        Ord Minnett Limited has bought/sold for you
        COMPANY:
        [next line] Company Name
    """
    reader = PdfReader(io.BytesIO(pdf_bytes))
    text = "\n".join(page.extract_text() or "" for page in reader.pages)
    lines = [l.strip() for l in text.splitlines() if l.strip()]

    fields = {
        "confirmation_date": None,
        "client_name": None,
        "platform": None,
        "account_number": None,
        "company_name": None,
        "transaction_type": None,
    }

    for i, line in enumerate(lines):

        # Confirmation Date: DD/MM/YYYY
        if not fields["confirmation_date"]:
            match = re.search(r"Confirmation Date[:\s]+(\d{2}/\d{2}/\d{4})", line, re.IGNORECASE)
            if match:
                raw_date = match.group(1)
                fields["confirmation_date"] = raw_date.replace("/", "")  # DDMMYYYY

        # Transaction type
        if not fields["transaction_type"]:
            if re.search(r"has bought for you", line, re.IGNORECASE):
                fields["transaction_type"] = "Bought"
            elif re.search(r"has sold for you", line, re.IGNORECASE):
                fields["transaction_type"] = "Sold"

        # Company name — line immediately after "COMPANY:"
        if re.search(r"^COMPANY\s*:?\s*$", line, re.IGNORECASE):
            if i + 1 < len(lines):
                fields["company_name"] = lines[i + 1].strip()

        # Client name — line immediately after "Client Name" label
        if re.search(r"^Client\s*Name\s*:?\s*$", line, re.IGNORECASE):
            if i + 1 < len(lines):
                fields["client_name"] = lines[i + 1].strip()

        # Platform + Account Number
        if fields["client_name"] and not fields["platform"]:
            platform_match = re.search(
                r"(Panorama|Netwealth|HUB24|BT Wrap|CFS|Colonial)[\s]+(\w+)",
                line, re.IGNORECASE
            )
            if platform_match:
                fields["platform"] = platform_match.group(1).strip()
                fields["account_number"] = platform_match.group(2).strip()

    return fields


def build_filename(fields: dict) -> str:
    """Construct filename from extracted fields."""
    date     = fields.get("confirmation_date") or "UNKNOWNDATE"
    client   = fields.get("client_name")       or "UnknownClient"
    platform = fields.get("platform")          or "UnknownPlatform"
    account  = fields.get("account_number")    or "UnknownAccount"
    company  = fields.get("company_name")      or "UnknownCompany"
    txn      = fields.get("transaction_type")  or "UnknownType"

    def clean(s):
        return re.sub(r'[\\/*?:"<>|]', "", s).strip()

    return f"{date} {clean(client)} {clean(platform)} {clean(account)} {clean(company)} {txn}.pdf"


# ── LOGGING ───────────────────────────────────────────────────────────────────

def log(message: str):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{timestamp}] {message}"
    print(line)
    with open(LOG_FILE, "a") as f:
        f.write(line + "\n")


# ── MAIN ──────────────────────────────────────────────────────────────────────

def main():
    OUTPUT_FOLDER.mkdir(parents=True, exist_ok=True)
    log("=" * 60)
    log(f"Run started — {'Ord Minnett only' if FILTER_BY_SENDER else 'ALL inbox emails'}")

    token = get_access_token()
    log("Authenticated with Microsoft Graph")

    messages = get_inbox_messages(token)
    log(f"Found {len(messages)} emails to process")

    if not messages:
        log("Nothing to process. Exiting.")
        return

    for msg in messages:
        subject = msg.get("subject", "No Subject")
        msg_id  = msg["id"]
        log(f"Processing: {subject}")

        if not msg.get("hasAttachments"):
            log(f"  SKIP — no attachments")
            archive_email(token, msg_id)
            continue

        attachments = get_attachments(token, msg_id)
        pdf_attachments = [a for a in attachments if a.get("name", "").endswith(".pdf")]

        if not pdf_attachments:
            log(f"  SKIP — no PDF attachments")
            archive_email(token, msg_id)
            continue

        for attachment in pdf_attachments:
            pdf_bytes = base64.b64decode(attachment["contentBytes"])

            fields = extract_pdf_fields(pdf_bytes)
            log(f"  Extracted: {fields}")

            filename = build_filename(fields)
            output_path = OUTPUT_FOLDER / filename

            with open(output_path, "wb") as f:
                f.write(pdf_bytes)
            log(f"  SAVED — {filename}")

        archive_email(token, msg_id)
        log(f"  ARCHIVED — {subject}")

    log("Run complete")
    log("=" * 60)


if __name__ == "__main__":
    main()
