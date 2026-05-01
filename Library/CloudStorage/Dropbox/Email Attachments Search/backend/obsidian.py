import os
import re
from urllib.parse import quote
from datetime import datetime

from backend.extraction import (
    extract_company,
    extract_company_from_filename,
    extract_date,
    extract_total_amount,
    extract_invoice_number,
)


def _vendor_slug(name: str) -> str:
    """Convert vendor name to lowercase slug with hyphens."""
    if not name:
        return "unknown"
    slug = name.lower()
    slug = re.sub(r"[^a-z0-9\s]", "", slug)
    slug = re.sub(r"\s+", "-", slug.strip())
    slug = re.sub(r"-+", "-", slug).strip("-")
    return slug or "unknown"


def _build_file_uri(absolute_path: str) -> str:
    """Convert absolute file path to file:// URI with proper encoding."""
    encoded = quote(absolute_path, safe="/:")
    return f"file://{encoded}"


def _parse_date(raw: str) -> str:
    """Parse date string in various formats to ISO 8601 (YYYY-MM-DD)."""
    if not raw:
        return ""
    
    # Try common formats
    for fmt in ("%d/%m/%Y", "%d-%m-%Y", "%Y-%m-%d", "%Y/%m/%d", "%d/%m/%y", "%d-%m-%y"):
        try:
            return datetime.strptime(raw, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    
    # Try regex fallback for unparseable but potentially valid date strings
    m = re.match(r"(\d{1,2})[/-](\d{1,2})[/-](\d{2,4})$", raw.strip())
    if m:
        d, mo, y = m.groups()
        y = f"20{y}" if len(y) == 2 else y
        try:
            return datetime(int(y), int(mo), int(d)).strftime("%Y-%m-%d")
        except ValueError:
            pass
    
    return raw


def extract_metadata_regex(text: str, filename: str) -> dict:
    """Extract document metadata using regex from text and filename."""
    raw_date = extract_date(text) or ""
    date = _parse_date(raw_date)
    year = date[:4] if len(date) >= 4 and date[:4].isdigit() else ""
    
    # Extract vendor: prefer text extraction, then filename extraction
    vendor_from_text = extract_company(text)
    vendor_from_filename = extract_company_from_filename(filename)
    
    # Use text extraction if available, else filename, else default to "Unknown"
    if vendor_from_text:
        vendor = vendor_from_text
    elif vendor_from_filename and vendor_from_filename.lower() != "unknown":
        # Only use filename extraction if it's not the default "unknown"
        vendor = vendor_from_filename
    else:
        vendor = "Unknown"
    
    amount_raw = extract_total_amount(text) or ""
    amount_num = re.sub(r"[^0-9.]", "", amount_raw)
    gst_num = ""
    if amount_num:
        try:
            total = float(amount_num)
            gst_num = f"{round(total - total / 1.15, 2):.2f}"
        except ValueError:
            pass
    
    return {
        "vendor": vendor,
        "date": date,
        "year": year,
        "amount_nzd": amount_num,
        "gst_nzd": gst_num,
        "invoice_number": extract_invoice_number(text) or "",
        "category": "",
        "due_date": "",
    }
