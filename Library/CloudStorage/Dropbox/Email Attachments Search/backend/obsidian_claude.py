import json
import os
import anthropic

from backend.obsidian import extract_metadata_regex

_SYSTEM_PROMPT = """You extract structured metadata from utility bill text.
Return ONLY a JSON object with these exact keys:
  vendor, date (YYYY-MM-DD), amount_nzd (numeric string, no $),
  gst_nzd (numeric string, no $), invoice_number, category, due_date (YYYY-MM-DD or empty).
category must be one of: utilities-electricity, utilities-gas, utilities-water,
  utilities-internet, insurance, rates, rent, subscription, other.
If a field cannot be determined, use an empty string."""

_USER_TEMPLATE = """Filename: {filename}

Bill text:
{text}"""


def extract_metadata_claude(text: str, filename: str) -> dict:
    """Extract bill metadata via the Claude API. Falls back to regex on any failure."""
    api_key = os.getenv("ANTHROPIC_API_KEY")

    try:
        client = anthropic.Anthropic(api_key=api_key)
        truncated = text[:3000] if len(text) > 3000 else text
        response = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=512,
            system=_SYSTEM_PROMPT,
            messages=[
                {
                    "role": "user",
                    "content": _USER_TEMPLATE.format(
                        filename=filename, text=truncated
                    ),
                }
            ],
        )
        raw = response.content[0].text.strip()
        raw = raw.removeprefix("```json").removeprefix("```").removesuffix("```").strip()
        metadata = json.loads(raw)
        for key in ("vendor", "date", "amount_nzd", "gst_nzd", "invoice_number", "category", "due_date"):
            metadata.setdefault(key, "")
        date = metadata.get("date", "")
        metadata["year"] = date[:4] if len(date) >= 4 and date[:4].isdigit() else ""
        return metadata
    except Exception:
        return extract_metadata_regex(text, filename)
