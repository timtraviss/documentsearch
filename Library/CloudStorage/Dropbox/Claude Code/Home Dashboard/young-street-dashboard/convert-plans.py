#!/usr/bin/env python3
"""Convert 11_Young_Street_plans.pdf to per-page PNGs for the floor plan viewer.

Usage:
    python3 convert-plans.py

Requires PyMuPDF:
    pip3 install pymupdf --break-system-packages
"""

import json
import sys
from pathlib import Path

PDF_PATH     = Path(__file__).parent.parent / "11_Young_Street_plans.pdf"
SCRIPT_DIR   = Path(__file__).parent
OUT_DIR      = SCRIPT_DIR / "plans"
PROPERTY_JSON = SCRIPT_DIR / "property.json"

try:
    import fitz
except ImportError:
    sys.exit("PyMuPDF not found. Install it with:\n  pip3 install pymupdf --break-system-packages")

if not PDF_PATH.exists():
    sys.exit(f"PDF not found at:\n  {PDF_PATH}")

OUT_DIR.mkdir(exist_ok=True)

doc = fitz.open(PDF_PATH)
count = len(doc)
print(f"Converting {count} page{'s' if count != 1 else ''}…")

for i, page in enumerate(doc, start=1):
    pix = page.get_pixmap(matrix=fitz.Matrix(2.0, 2.0))
    out = OUT_DIR / f"page-{i:02d}.png"
    pix.save(out)
    print(f"  {out.name}  ({pix.width}×{pix.height}px)")

doc.close()

data = json.loads(PROPERTY_JSON.read_text())
data["floorPlan"] = {"pageCount": count}
PROPERTY_JSON.write_text(json.dumps(data, indent=2) + "\n")

print(f"\n✓ plans/ folder: {count} images written")
print(f"✓ property.json updated → floorPlan.pageCount = {count}")
print(f"✓ Reload the dashboard — the 📐 button will appear in the top-right.")
