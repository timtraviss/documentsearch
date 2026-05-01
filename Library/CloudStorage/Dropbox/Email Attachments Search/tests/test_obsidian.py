import os
import pytest
from backend.obsidian import (
    _vendor_slug,
    _build_file_uri,
    _parse_date,
    extract_metadata_regex,
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
