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


def _yaml_str(value: str) -> str:
    """Return value as a safely double-quoted YAML scalar."""
    escaped = value.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def render_sidecar(metadata: dict, text: str, file_uri: str) -> str:
    """Return a UTF-8 Markdown string with YAML frontmatter for an Obsidian bill note."""
    vendor = metadata.get("vendor", "Unknown")
    date = metadata.get("date", "")
    year = metadata.get("year", "")
    amount = metadata.get("amount_nzd", "")
    gst = metadata.get("gst_nzd", "")
    invoice_number = metadata.get("invoice_number", "")
    category = metadata.get("category", "")
    due_date = metadata.get("due_date", "")

    tags = ['"bill"', f'"{_vendor_slug(vendor)}"']
    if category:
        tags.append(f'"{category}"')
    if year:
        tags.append(f'"{year}"')
    tags_str = "[" + ", ".join(tags) + "]"

    try:
        amount_display = f"${float(amount):,.2f}" if amount else ""
        gst_display = f"${float(gst):,.2f}" if gst else ""
    except ValueError:
        amount_display = amount
        gst_display = gst

    lines = [
        "---",
        "type: bill",
        f"vendor: {_yaml_str(vendor)}",
        f"date: {_yaml_str(date)}",
        f"amount_nzd: {amount}",
        f"gst_nzd: {gst}",
        f"invoice_number: {_yaml_str(invoice_number)}",
        f"category: {_yaml_str(category)}",
        f"due_date: {_yaml_str(due_date)}",
        "paid: false",
        f'file_uri: "{file_uri}"',
        f"tags: {tags_str}",
        "---",
        "",
        f"# {vendor}",
        "",
    ]

    if amount_display:
        gst_suffix = f" (incl. {gst_display} GST)" if gst_display else ""
        lines.append(f"**Amount:** {amount_display}{gst_suffix}")
    if due_date:
        lines.append(f"**Due:** {due_date}")
    if invoice_number:
        lines.append(f"**Invoice:** {invoice_number}")

    lines.append(f"\n[Open original PDF]({file_uri})")

    if text.strip():
        lines.extend(["", "## Extracted text", "", text.strip()])

    lines.append("")
    return "\n".join(lines)


def export_to_obsidian(
    doc: dict,
    vault_path: str,
    mode: str = "regex",
) -> tuple[bool, str]:
    """Write Bills/<year>/<date>-<vendor-slug>.md to vault_path.

    Returns (True, path) on write, (False, path) if already exists.
    mode='claude' delegates extraction to extract_metadata_claude (lazy import).
    """
    text = doc.get("text", "")
    filename = doc.get("filename", "")
    absolute_path = doc.get("path", "")

    if mode == "claude":
        from backend.obsidian_claude import extract_metadata_claude
        metadata = extract_metadata_claude(text, filename)
    else:
        metadata = extract_metadata_regex(text, filename)

    date = metadata.get("date") or "unknown"
    year = metadata.get("year") or (date[:4] if date != "unknown" and date[:4].isdigit() else "unknown")
    slug = _vendor_slug(metadata.get("vendor", ""))

    md_filename = f"{date}-{slug}.md"
    target_dir = os.path.join(vault_path, "Bills", year)
    target_path = os.path.join(target_dir, md_filename)

    if os.path.exists(target_path):
        return False, target_path

    file_uri = _build_file_uri(absolute_path) if absolute_path else ""
    content = render_sidecar(metadata, text, file_uri)

    os.makedirs(target_dir, exist_ok=True)
    with open(target_path, "w", encoding="utf-8") as f:
        f.write(content)

    return True, target_path
