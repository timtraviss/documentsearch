import os
import pytest
from backend.obsidian import (
    _vendor_slug,
    _build_file_uri,
    _parse_date,
    extract_metadata_regex,
    render_sidecar,
    export_to_obsidian,
)

BILL_TEXT = """Mercury Energy
Invoice Date: 15/04/2026
Invoice Number: INV-29384756
Due Date: 30/04/2026
Total Due: $187.45 NZD
"""


# --- _vendor_slug ---

def test_vendor_slug_basic():
    assert _vendor_slug("Mercury Energy") == "mercury-energy"


def test_vendor_slug_special_chars():
    assert _vendor_slug("Z Energy & Gas Ltd") == "z-energy-gas-ltd"


def test_vendor_slug_empty():
    assert _vendor_slug("") == "unknown"


def test_vendor_slug_numbers():
    assert _vendor_slug("Watercare 2024") == "watercare-2024"


# --- _build_file_uri ---

def test_build_file_uri_no_spaces():
    uri = _build_file_uri("/Users/tim/Dropbox/Email Attachments/bill.pdf")
    assert uri == "file:///Users/tim/Dropbox/Email%20Attachments/bill.pdf"


def test_build_file_uri_preserves_slashes():
    uri = _build_file_uri("/a/b/c.pdf")
    assert uri.startswith("file:///a/b/c.pdf")


# --- _parse_date ---

def test_parse_date_dmy_slash():
    assert _parse_date("15/04/2026") == "2026-04-15"


def test_parse_date_dmy_dash():
    assert _parse_date("15-04-2026") == "2026-04-15"


def test_parse_date_ymd():
    assert _parse_date("2026-04-15") == "2026-04-15"


def test_parse_date_two_digit_year():
    assert _parse_date("15/04/26") == "2026-04-15"


def test_parse_date_unparseable():
    assert _parse_date("April 2026") == "April 2026"


def test_parse_date_empty():
    assert _parse_date("") == ""


# --- extract_metadata_regex ---

def test_extract_metadata_regex_vendor():
    meta = extract_metadata_regex(BILL_TEXT, "Mercury_Energy_April_2026.pdf")
    assert meta["vendor"] == "Mercury Energy"


def test_extract_metadata_regex_date():
    meta = extract_metadata_regex(BILL_TEXT, "bill.pdf")
    assert meta["date"] == "2026-04-15"


def test_extract_metadata_regex_year():
    meta = extract_metadata_regex(BILL_TEXT, "bill.pdf")
    assert meta["year"] == "2026"


def test_extract_metadata_regex_amount():
    meta = extract_metadata_regex(BILL_TEXT, "bill.pdf")
    assert meta["amount_nzd"] == "187.45"


def test_extract_metadata_regex_gst():
    meta = extract_metadata_regex(BILL_TEXT, "bill.pdf")
    # GST = 187.45 - 187.45/1.15 ≈ 24.45
    assert meta["gst_nzd"] == "24.45"


def test_extract_metadata_regex_invoice_number():
    meta = extract_metadata_regex(BILL_TEXT, "bill.pdf")
    assert meta["invoice_number"] == "INV-29384756"


def test_extract_metadata_regex_empty_text():
    meta = extract_metadata_regex("", "unknown.pdf")
    assert meta["vendor"] == "Unknown"
    assert meta["date"] == ""
    assert meta["amount_nzd"] == ""


FULL_METADATA = {
    "vendor": "Mercury Energy",
    "date": "2026-04-15",
    "year": "2026",
    "amount_nzd": "187.45",
    "gst_nzd": "24.45",
    "invoice_number": "INV-29384756",
    "category": "",
    "due_date": "",
}


# --- render_sidecar ---

def test_render_sidecar_contains_frontmatter():
    content = render_sidecar(FULL_METADATA, "some text", "file:///path/bill.pdf")
    assert content.startswith("---\n")
    assert "type: bill" in content
    assert 'vendor: "Mercury Energy"' in content
    assert "amount_nzd: 187.45" in content


def test_render_sidecar_contains_body():
    content = render_sidecar(FULL_METADATA, "some text", "file:///path/bill.pdf")
    assert "# Mercury Energy" in content
    assert "**Amount:** $187.45" in content
    assert "[Open original PDF]" in content


def test_render_sidecar_includes_extracted_text():
    content = render_sidecar(FULL_METADATA, "raw bill text here", "file:///x.pdf")
    assert "## Extracted text" in content
    assert "raw bill text here" in content


def test_render_sidecar_skips_extracted_text_when_empty():
    content = render_sidecar(FULL_METADATA, "", "file:///x.pdf")
    assert "## Extracted text" not in content


def test_render_sidecar_tags_include_vendor_and_year():
    content = render_sidecar(FULL_METADATA, "", "file:///x.pdf")
    assert "mercury-energy" in content
    assert "2026" in content


# --- export_to_obsidian ---

def test_export_creates_file(tmp_path):
    doc = {
        "path": "/Dropbox/Email Attachments/Mercury_April_2026.pdf",
        "filename": "Mercury_April_2026.pdf",
        "text": BILL_TEXT,
    }
    wrote, dest = export_to_obsidian(doc, str(tmp_path))
    assert wrote is True
    assert os.path.exists(dest)
    assert dest.endswith("2026-04-15-mercury-energy.md")


def test_export_creates_year_subfolder(tmp_path):
    doc = {
        "path": "/Dropbox/Email Attachments/Mercury_April_2026.pdf",
        "filename": "Mercury_April_2026.pdf",
        "text": BILL_TEXT,
    }
    _, dest = export_to_obsidian(doc, str(tmp_path))
    assert os.path.join("Bills", "2026") in dest


def test_export_is_idempotent(tmp_path):
    doc = {
        "path": "/Dropbox/Email Attachments/Mercury_April_2026.pdf",
        "filename": "Mercury_April_2026.pdf",
        "text": BILL_TEXT,
    }
    wrote1, dest1 = export_to_obsidian(doc, str(tmp_path))
    wrote2, dest2 = export_to_obsidian(doc, str(tmp_path))
    assert wrote1 is True
    assert wrote2 is False  # already exists — skip
    assert dest1 == dest2


def test_export_handles_empty_text(tmp_path):
    doc = {
        "path": "/Dropbox/Email Attachments/unknown.pdf",
        "filename": "unknown.pdf",
        "text": "",
    }
    wrote, dest = export_to_obsidian(doc, str(tmp_path))
    assert wrote is True
    assert os.path.exists(dest)


def test_render_sidecar_vendor_with_colon_is_valid_yaml():
    import yaml
    meta = {**FULL_METADATA, "vendor": "Vector: Lines NZ"}
    content = render_sidecar(meta, "", "file:///x.pdf")
    # Extract frontmatter between the two --- delimiters
    parts = content.split("---")
    frontmatter = yaml.safe_load(parts[1])
    assert frontmatter["vendor"] == "Vector: Lines NZ"
