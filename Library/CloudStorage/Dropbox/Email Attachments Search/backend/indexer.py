import os
import json
from pdfminer.high_level import extract_text
from dotenv import load_dotenv

# Load configuration
load_dotenv()
# allow overriding via environment; fall back to a sensible default
PDF_FOLDER = os.getenv("PDF_FOLDER") or os.path.expanduser(
    "~/Library/CloudStorage/Dropbox/Email Attachments Search/Email Attachments"
)

INDEX_FILE = os.path.join(os.path.dirname(__file__), "index.json")


def scan_pdfs(folder, progress_callback=None, existing_index=None):
    """Recursively scan folder for PDF files and extract text.

    If `progress_callback` is provided it will be called for each file with
    the signature: progress_callback(absolute_path, index, total, skipped=False)

    If `existing_index` is provided (list of dicts from a previous index), files
    whose mtime matches the stored value are reused without re-extracting text
    (incremental mode).  Files that were deleted are dropped automatically.
    """
    # Build lookup from a previous index: path -> doc (only entries with mtime)
    cached = {}
    if existing_index:
        for doc in existing_index:
            if "path" in doc and "mtime" in doc:
                cached[doc["path"]] = doc

    docs = []
    pdf_files = []
    for root, dirs, files in os.walk(folder):
        for filename in files:
            if filename.lower().endswith(".pdf"):
                pdf_files.append((root, filename))

    total = len(pdf_files)
    for idx, (root, filename) in enumerate(pdf_files, start=1):
        absolute_path = os.path.join(root, filename)
        relative_path = os.path.relpath(absolute_path, folder)

        try:
            current_mtime = os.path.getmtime(absolute_path)
        except OSError:
            current_mtime = None

        # Reuse cached entry when mtime is unchanged
        if current_mtime is not None and absolute_path in cached:
            if cached[absolute_path].get("mtime") == current_mtime:
                docs.append(cached[absolute_path])
                if progress_callback:
                    try:
                        progress_callback(absolute_path, idx, total, skipped=True)
                    except Exception:
                        pass
                continue

        try:
            text = extract_text(absolute_path)
        except Exception as e:
            print(f"Failed to read {absolute_path}: {e}")
            text = ""

        doc = {
            "path": absolute_path,
            "relative_path": relative_path,
            "filename": filename,
            "text": text,
        }
        if current_mtime is not None:
            doc["mtime"] = current_mtime

        docs.append(doc)

        if progress_callback:
            try:
                progress_callback(absolute_path, idx, total, skipped=False)
            except Exception:
                # Never let a progress callback break indexing
                pass

    return docs


def save_index(docs):
    with open(INDEX_FILE, "w", encoding="utf-8") as f:
        json.dump(docs, f, indent=2)
    print(f"Saved index to {INDEX_FILE} ({len(docs)} documents)")


if __name__ == "__main__":
    if not PDF_FOLDER or not os.path.isdir(PDF_FOLDER):
        print("PDF_FOLDER not configured or does not exist. Please set the PDF_FOLDER environment variable or update the default path.")
        exit(1)

    documents = scan_pdfs(PDF_FOLDER)
    save_index(documents)
