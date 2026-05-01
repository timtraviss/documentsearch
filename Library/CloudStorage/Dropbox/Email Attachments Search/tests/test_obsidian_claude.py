import pytest
from unittest.mock import patch, MagicMock
from backend.obsidian_claude import extract_metadata_claude

BILL_TEXT = """Mercury Energy
Invoice Date: 15/04/2026
Invoice Number: INV-29384756
Total Due: $187.45 NZD
"""

MOCK_RESPONSE_JSON = """{
  "vendor": "Mercury Energy",
  "date": "2026-04-15",
  "amount_nzd": "187.45",
  "gst_nzd": "24.45",
  "invoice_number": "INV-29384756",
  "category": "utilities-electricity",
  "due_date": ""
}"""


@patch("backend.obsidian_claude.anthropic.Anthropic")
def test_extract_metadata_claude_returns_dict(mock_anthropic_class):
    mock_client = MagicMock()
    mock_anthropic_class.return_value = mock_client
    mock_client.messages.create.return_value = MagicMock(
        content=[MagicMock(text=MOCK_RESPONSE_JSON)]
    )

    result = extract_metadata_claude(BILL_TEXT, "Mercury_April_2026.pdf")

    assert result["vendor"] == "Mercury Energy"
    assert result["date"] == "2026-04-15"
    assert result["amount_nzd"] == "187.45"
    assert result["invoice_number"] == "INV-29384756"
    assert result["category"] == "utilities-electricity"


@patch("backend.obsidian_claude.anthropic.Anthropic")
def test_extract_metadata_claude_falls_back_on_bad_json(mock_anthropic_class):
    mock_client = MagicMock()
    mock_anthropic_class.return_value = mock_client
    mock_client.messages.create.return_value = MagicMock(
        content=[MagicMock(text="not valid json")]
    )

    result = extract_metadata_claude(BILL_TEXT, "Mercury_April_2026.pdf")

    # Falls back to regex extraction — vendor should still be set
    assert result["vendor"] != ""


@patch("backend.obsidian_claude.anthropic.Anthropic")
def test_extract_metadata_claude_falls_back_on_api_error(mock_anthropic_class):
    mock_client = MagicMock()
    mock_anthropic_class.return_value = mock_client
    mock_client.messages.create.side_effect = Exception("API error")

    result = extract_metadata_claude(BILL_TEXT, "Mercury_April_2026.pdf")

    # Falls back to regex — should not raise
    assert isinstance(result, dict)
    assert "vendor" in result


@patch.dict("os.environ", {}, clear=False)
def test_extract_metadata_claude_falls_back_when_no_api_key(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

    result = extract_metadata_claude(BILL_TEXT, "Mercury_April_2026.pdf")

    # No key → falls back to regex, still returns a dict
    assert isinstance(result, dict)
    assert "vendor" in result


@patch("backend.obsidian_claude.anthropic.Anthropic")
def test_extract_metadata_claude_strips_markdown_fences(mock_anthropic_class):
    mock_client = MagicMock()
    mock_anthropic_class.return_value = mock_client
    fenced = f"```json\n{MOCK_RESPONSE_JSON}\n```"
    mock_client.messages.create.return_value = MagicMock(
        content=[MagicMock(text=fenced)]
    )
    result = extract_metadata_claude(BILL_TEXT, "Mercury_April_2026.pdf")
    assert result["vendor"] == "Mercury Energy"
