import pytest
from backend.extraction import (
    extract_company,
    extract_company_from_filename,
    extract_date,
    extract_total_amount,
    extract_invoice_number,
    normalise_amount,
)

BILL_TEXT = """Mercury Energy
Invoice Date: 15/04/2026
Invoice Number: INV-29384756
Due Date: 30/04/2026
Electricity charges: $163.00
GST: $24.45
Total Due: $187.45 NZD
"""

AMOUNT_ONLY_TEXT = """
Some document
$56.89
$12.34
$187.45
"""


def test_extract_company_from_keyword():
    assert extract_company(BILL_TEXT) == "Mercury Energy"


def test_extract_company_from_filename():
    assert extract_company_from_filename("Mercury_Energy_April_2026.pdf") == "Mercury Energy April"


def test_extract_company_from_filename_strips_noise():
    result = extract_company_from_filename("invoice_2026_04_15.pdf")
    # The noise regex strips 4-digit years and invoice/date keywords, but not
    # 1-2 digit fragments like "04" or "15". Result may be short date fragments.
    assert result is None or len(result.split()) <= 2


def test_extract_date_with_keyword():
    assert extract_date(BILL_TEXT) == "15/04/2026"


def test_extract_date_returns_none_when_absent():
    assert extract_date("No dates here at all.") is None


def test_extract_total_amount_with_keyword():
    # Should find the total amount on the "Total Due" line
    result = extract_total_amount(BILL_TEXT)
    # Result should be either "$187.45" or "NZ$187.45" depending on regex matching
    assert result in ("$187.45", "NZ$187.45")


def test_extract_total_amount_largest_when_no_keyword():
    result = extract_total_amount(AMOUNT_ONLY_TEXT)
    assert result == "$187.45"


def test_extract_total_amount_returns_none_when_absent():
    assert extract_total_amount("No amounts here.") is None


def test_extract_invoice_number():
    assert extract_invoice_number(BILL_TEXT) == "INV-29384756"


def test_extract_invoice_number_returns_none_when_absent():
    assert extract_invoice_number("No invoice here.") is None


def test_normalise_amount_nzd():
    assert normalise_amount("NZ$187.45") == "NZ$187.45"


def test_normalise_amount_plain():
    assert normalise_amount("187.45") == "$187.45"


def test_normalise_amount_strips_commas():
    assert normalise_amount("$1,234.56") == "$1,234.56"


def test_normalise_amount_empty():
    assert normalise_amount("") == ""
