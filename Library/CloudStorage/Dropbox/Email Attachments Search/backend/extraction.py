import os
import re


def extract_company_from_filename(filename):
    name = os.path.splitext(filename)[0]
    name = re.sub(r"[_\-]+", " ", name)
    noise = (r"\b(invoice|receipt|statement|quote|contract|tax|gst|nz|pdf|"
             r"final|draft|copy|order|ref|no|number|"
             r"\d{4}|\d{1,2}[/-]\d{1,2}(?:[/-]\d{2,4})?)\b")
    cleaned = re.sub(noise, "", name, flags=re.IGNORECASE).strip()
    words = [w for w in cleaned.split() if len(w) > 1]
    return " ".join(words[:3]) if words else None


def extract_company(text):
    lines = text.split("\n")
    company_keywords = ["from:", "vendor:", "billed by:", "company:", "invoice from:"]
    for line in lines[:30]:
        line_lower = line.lower()
        for keyword in company_keywords:
            if keyword in line_lower:
                parts = line.split(":")
                if len(parts) > 1:
                    company = parts[-1].strip()
                    if company and len(company) > 2:
                        return company[:100]
    for line in lines[:20]:
        line = line.strip()
        if line and 5 < len(line) < 80:
            if any(c.isupper() for c in line) and not any(c.isdigit() for c in line[:5]):
                return line
    return None


def extract_date(text):
    keywords = ["date:", "date ", "dated ", "invoice date:"]
    lines = text.split("\n")
    for line in lines[:30]:
        if any(kw in line.lower() for kw in keywords):
            dates = re.findall(
                r"(\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\d{4}[/-]\d{1,2}[/-]\d{1,2})",
                line,
            )
            if dates:
                return dates[0]
    all_dates = re.findall(
        r"(\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\d{4}[/-]\d{1,2}[/-]\d{1,2})",
        text[:500],
    )
    return all_dates[0] if all_dates else None


def normalise_amount(raw):
    if not raw:
        return ""
    raw = str(raw).strip()
    nzd = bool(re.search(r"NZ\$|NZD", raw, re.IGNORECASE))
    digits = re.sub(r"[^\d.]", "", raw)
    if not digits:
        return raw
    try:
        value = float(digits)
    except ValueError:
        return raw
    prefix = "NZ$" if nzd else "$"
    return f"{prefix}{value:,.2f}"


def extract_total_amount(text):
    keywords = ["total:", "amount due:", "total amount:", "invoice total:", "balance due:"]
    for line in text.split("\n"):
        if any(kw in line.lower() for kw in keywords):
            amounts = re.findall(
                r"\$[\d,]+\.?\d{0,2}|NZ\$[\d,]+\.?\d{0,2}|[\d,]+\.\d{2}(?:\s*NZD?)?",
                line,
            )
            if amounts:
                return normalise_amount(amounts[-1])
    all_amounts = re.findall(r"\$[\d,]+\.?\d{0,2}|NZ\$[\d,]+\.?\d{0,2}", text)
    if all_amounts:
        try:
            largest = max(all_amounts, key=lambda s: float(re.sub(r"[^\d.]", "", s)))
            return normalise_amount(largest)
        except Exception:
            return normalise_amount(all_amounts[-1])
    return None


def extract_invoice_number(text):
    keywords = ["invoice #:", "invoice no:", "invoice number:", "ref:", "reference:", "inv#:"]
    for line in text.split("\n")[:40]:
        if any(kw in line.lower() for kw in keywords):
            parts = line.split(":")
            if len(parts) > 1:
                num = parts[-1].strip().split()[0] if parts[-1].strip() else ""
                if num and len(num) < 30 and any(c.isdigit() for c in num):
                    return num
    return None
