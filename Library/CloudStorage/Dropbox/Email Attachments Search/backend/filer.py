"""
filer.py — File loose PDFs from the PDF_FOLDER root into company subfolders.

Adapted from the update-bills-spreadsheet skill's file_bills.py.
Uses pdfminer (already a project dependency) instead of pdftotext.
"""

import re
import shutil
from datetime import datetime
from pathlib import Path

from pdfminer.high_level import extract_text as _pdfminer_extract


KNOWN_COMPANIES = [
    (r"watercare",                           "Water - Watercare",                    "Utilities"),
    (r"artesian\s*[&and]+\s*solway",         "Water - Artesian & Solway",            "Utilities"),
    (r"genesis\s*energy",                    "Genesis Energy",                       "Utilities"),
    (r"northland\s*waste",                   "Northland Waste",                      "Utilities"),
    (r"auckland\s*council",                  "Council Rates",                        "Government"),
    (r"kaipara\s*district\s*council",        "Council Rates",                        "Government"),
    (r"rodney\s*district\s*council",         "Council Rates",                        "Government"),
    (r"far\s*north\s*district",              "Council Rates",                        "Government"),
    (r"auckland\s*transport\b",              "Auckland Transport",                   "Transport / Government"),
    (r"\bAT\b.*auckland\s*transport",        "Auckland Transport",                   "Transport / Government"),
    (r"central\s*landscapes",                "Central Landscapes",                   "Landscaping & Supplies"),
    (r"green\s*matter",                      "Green Matter",                         "Landscaping & Supplies"),
    (r"j\s*[&and]+\s*s\s*gardens",           "J&S Gardens",                          "Landscaping & Supplies"),
    (r"kaipara\s*coast\s*plant",             "Receipts/Kaipara Coast Plant Centre",  "Supplies"),
    (r"amx\s*structures",                    "AMX Structures",                       "Construction"),
    (r"david\s*reid\s*homes",                "David Reid Homes",                     "Construction"),
    (r"drh\s*north\s*shore|drh\s*\(north\s*shore\)", "DRH (North Shore) Ltd",        "Construction"),
    (r"drinnan\s*contractors",               "Drinnan Contractors",                  "Trades"),
    (r"shire\s*engineering",                 "Shire Engineering",                    "Trades"),
    (r"little\s*digger\s*company",           "The Little Digger Company",            "Trades"),
    (r"tree\s*contracts",                    "Tree Contracts",                       "Trades"),
    (r"urban\s*planner",                     "The Urban Planner",                    "Professional Services"),
    (r"matakana\s*itm",                      "Matakana ITM",                         "Building Supplies"),
    (r"warkworth\s*itm",                     "Warkworth ITM",                        "Building Supplies"),
    (r"axial\s*appliance",                   "Axial Appliance Servicing",            "Home Maintenance"),
    (r"tower\s*insurance",                   "Tower Insurance",                      "Insurance"),
    (r"police\s*health\s*plan",              "Police Health Plan",                   "Insurance / Benefits"),
    (r"police\s*welfare\s*fund",             "Police Welfare Fund",                  "Insurance / Benefits"),
    (r"lila\s*school",                       "Lila School of Bands",                 "Education"),
    (r"selwyn\s*college",                    "Receipts/Selwyn College",              "Education"),
    (r"jb\s*hi[- ]?fi",                      "JB Hi-Fi",                             "Supplies / Electronics"),
    (r"as\s*colour",                         "AS Colour",                            "Supplies"),
    (r"awarua\s*trading",                    "Awarua Trading",                       "Supplies"),
    (r"magma\s*enterprises",                 "Magma Enterprises",                    "Supplies"),
    (r"manuhiri\s*kaitiaki",                 "Manuhiri Kaitiaki Trust",              "Donations"),
    (r"evernote",                            "Evernote",                             "Software / Productivity"),
    (r"anthropic",                           "Receipts/Anthropic",                   "Software / Productivity"),
    (r"midjourney",                          "Receipts/Midjourney",                  "Software / Productivity"),
    (r"eleven\s*labs",                       "Receipts/ElevenLabs",                  "Software / Productivity"),
    (r"lets\s*enhance",                      "Receipts/Lets Enhance",                "Software / Productivity"),
    (r"\brender\b",                          "Receipts/Render",                      "Software / Productivity"),
    (r"apple\s+inc|apple\.com",              "Receipts/Apple",                       "Software / Productivity"),
    (r"\bnzta\b|nz\s*transport\s*agency",    "Receipts/NZTA",                        "Transport / Government"),
    (r"stroke\s*aotearoa",                   "Receipts/Stroke Aotearoa NZ",          "Donations"),
    (r"royal\s*nz\s*coastguard|coastguard\s*nz", "Receipts/Royal NZ Coastguard",    "Donations"),
    (r"artesian\s*&\s*solway\s*water",       "Receipts/Artesian & Solway Water",     "Utilities"),
    (r"\bdescript\b",                        "Receipts/Descript",                    "Software / Productivity"),
    (r"active\s*automotive",                 "Active Automotive Services",           "Trades"),
]

INVOICE_KEYWORDS = re.compile(
    r"tax\s*invoice|invoice\s*no|invoice\s*number|invoice\s*date"
    r"|amount\s*due|amount\s*payable|total\s*due|gst\s*invoice"
    r"|please\s*pay|remittance|statement\s*of\s*account"
    r"|progress\s*claim|payment\s*due|rates\s*(notice|invoice|assessment)"
    r"|\breceipt\b|\bpurchase\s*order\b",
    re.IGNORECASE,
)

NOT_INVOICE_KEYWORDS = re.compile(
    r"inspection\s*report|homeowners?\s*manual|resource\s*consent"
    r"|building\s*consent|valuation\s*report|property\s*report"
    r"|working\s*with\s*children|wwcc|docusign.*form|construction\s*plan"
    r"|no\s*referral|map\s*of",
    re.IGNORECASE,
)

INVOICE_FILENAME_HINTS = re.compile(
    r"invoice|receipt|bill|rates|statement|tax",
    re.IGNORECASE,
)

NON_BILLING_FOLDERS = {
    "Training Materials", "Work Documents", "Holly Traviss Writing",
    "Legal & Forms", "Medical", "Miscellaneous", "Finance & Tax",
    "Building Consent", "Insurance", "Property & Valuations",
    "Invoices", "Vehicle",
}


def _extract_text(pdf_path: Path) -> str:
    try:
        return _pdfminer_extract(str(pdf_path)) or ""
    except Exception:
        return ""


def _is_invoice(filename: str, text: str) -> bool:
    if NOT_INVOICE_KEYWORDS.search(filename) or NOT_INVOICE_KEYWORDS.search(text[:1000]):
        return False
    if INVOICE_FILENAME_HINTS.search(filename):
        return True
    if INVOICE_KEYWORDS.search(text[:3000]):
        return True
    has_dollar = bool(re.search(r"\$\s*[\d,]+\.\d{2}", text))
    has_gst = bool(re.search(r"\bGST\b", text))
    return has_dollar and has_gst


def _identify_company(filename: str, text: str) -> tuple:
    combined = filename + "\n" + text[:4000]
    for pattern, folder_name, category in KNOWN_COMPANIES:
        if re.search(pattern, combined, re.IGNORECASE):
            return folder_name, category
    return None, None


def _extract_date(text: str, filename: str = "") -> str:
    patterns = [
        r"[Ii]nvoice\s+[Dd]ate[:\s]+(\d{1,2}[/\-]\d{1,2}[/\-]\d{4})",
        r"[Ii]ssued\s+[Dd]ate[:\s]+(\d{1,2}[/\-]\d{1,2}[/\-]\d{4})",
        r"[Ss]tatement\s+[Dd]ate[:\s]+(\d{1,2}[/\-]\d{1,2}[/\-]\d{4})",
        r"[Pp]eriod\s+[Ee]nding[:\s]+(\d{1,2}[/\-]\d{1,2}[/\-]\d{4})",
        r"[Dd]ate[:\s]+(\d{1,2}[/\-]\d{1,2}[/\-]\d{4})",
        r"(\d{1,2}\s+(?:January|February|March|April|May|June|July|August|"
        r"September|October|November|December)\s+\d{4})",
        r"((?:January|February|March|April|May|June|July|August|"
        r"September|October|November|December)\s+\d{1,2},?\s+\d{4})",
        r"(\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d{4})",
        r"(\d{1,2}/\d{1,2}/\d{4})",
        r"(\d{1,2}-\d{1,2}-\d{4})",
    ]
    for pat in patterns:
        m = re.search(pat, text[:3000])
        if m:
            return m.group(1)
    m = re.search(r"(\d{4}-\d{2}-\d{2})", filename)
    if m:
        return m.group(1)
    return ""


def _normalise_date(raw: str) -> str:
    if not raw:
        return None
    if re.match(r"^\d{4}-\d{2}-\d{2}$", raw):
        return raw
    for fmt in ("%d/%m/%Y", "%d-%m-%Y", "%d %B %Y", "%B %d, %Y", "%d %b %Y"):
        try:
            return datetime.strptime(raw, fmt).strftime("%Y-%m-%d")
        except ValueError:
            pass
    return None


def _resolve_folder(folder_name: str, workspace: Path) -> str:
    if "/" in folder_name:
        return folder_name
    normalised = folder_name.lower().strip()
    for existing in workspace.iterdir():
        if existing.is_dir() and existing.name.lower() == normalised:
            return existing.name
    return re.sub(r'[<>:"/\\|?*]', "", folder_name).strip()


def _slug(folder_name: str) -> str:
    return re.sub(r"[^A-Za-z0-9]+", "", folder_name.replace("&", "And"))


def _dest_path(folder: Path, slug: str, date: str) -> Path:
    base = f"{slug}_{date}"
    candidate = folder / f"{base}.pdf"
    n = 2
    while candidate.exists():
        candidate = folder / f"{base}_{n}.pdf"
        n += 1
    return candidate


def process_workspace(workspace: Path, dry_run: bool = False, progress_cb=None) -> dict:
    """
    Scan workspace root for loose PDFs and file them into company subfolders.

    progress_cb(message: str) is called for each log line if provided.
    Returns {"filed": [...], "skipped_not_invoice": [...], "skipped_unidentified": [...]}
    """
    def log(msg):
        if progress_cb:
            progress_cb(msg)

    results = {"filed": [], "skipped_not_invoice": [], "skipped_unidentified": []}

    loose = sorted(p for p in workspace.iterdir()
                   if p.is_file() and p.suffix.lower() == ".pdf")

    if not loose:
        log("No loose PDFs found in root folder.")
        return results

    log(f"Found {len(loose)} loose PDF(s) to process...")

    for pdf in loose:
        fname = pdf.name
        log(f"  {fname}")
        text = _extract_text(pdf)

        if not _is_invoice(fname, text):
            log("    → not an invoice, leaving in place")
            results["skipped_not_invoice"].append(fname)
            continue

        company, category = _identify_company(fname, text)
        if not company:
            log("    → company not recognised, leaving in place")
            results["skipped_unidentified"].append(fname)
            continue

        date = _normalise_date(_extract_date(text, fname))
        if not date:
            date = datetime.today().strftime("%Y-%m-%d")
            log(f"    → no date found, using today ({date})")

        folder_name = _resolve_folder(company, workspace)
        if folder_name in NON_BILLING_FOLDERS:
            log(f"    → resolved to non-billing folder '{folder_name}', leaving in place")
            results["skipped_unidentified"].append(fname)
            continue

        target_folder = workspace / folder_name
        dest = _dest_path(target_folder, _slug(folder_name), date)

        log(f"    → {folder_name}/{dest.name}")

        if not dry_run:
            target_folder.mkdir(exist_ok=True)
            shutil.move(str(pdf), str(dest))

        results["filed"].append({
            "original": fname,
            "destination": f"{folder_name}/{dest.name}",
            "company": company,
            "date": date,
            "category": category,
        })

    filed = len(results["filed"])
    skipped = len(results["skipped_not_invoice"]) + len(results["skipped_unidentified"])
    log(f"Done. {filed} filed, {skipped} left in place.")
    return results
