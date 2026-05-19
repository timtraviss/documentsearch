import os
import json
from pdfminer.high_level import extract_text
from database import get_all_documents, upsert_document

PROPERTY_JSON = os.path.abspath(
    os.path.join(os.path.dirname(__file__), '..', 'property.json')
)


def load_doc_names():
    """Return {lowercase_name: display_name} from property.json documents array."""
    try:
        with open(PROPERTY_JSON) as f:
            data = json.load(f)
        return {d['name'].lower(): d['name'] for d in data.get('documents', [])}
    except Exception:
        return {}


def scan_pdfs(folder, progress_callback=None):
    """
    Walk folder for PDFs, skip files with matching mtime, extract and index new ones.
    Returns (indexed_count, skipped_count).
    """
    existing = {d['path']: d['mtime'] for d in get_all_documents()}
    doc_names = load_doc_names()

    pdf_paths = []
    for root, _, files in os.walk(folder):
        for fname in sorted(files):
            if fname.lower().endswith('.pdf'):
                pdf_paths.append(os.path.join(root, fname))

    indexed = 0
    skipped = 0
    total = len(pdf_paths)

    for i, path in enumerate(pdf_paths):
        mtime = os.path.getmtime(path)
        filename = os.path.basename(path)
        stem = os.path.splitext(filename)[0]
        name = doc_names.get(stem.lower(), stem)

        if progress_callback:
            progress_callback(f'{i + 1}/{total} {filename}')

        if path in existing and existing[path] == mtime:
            skipped += 1
            continue

        try:
            text = extract_text(path) or ''
        except Exception as exc:
            if progress_callback:
                progress_callback(f'ERROR {filename}: {exc}')
            continue

        upsert_document(
            path=path, filename=filename, name=name,
            mtime=mtime, text=text,
        )
        indexed += 1

    return indexed, skipped
