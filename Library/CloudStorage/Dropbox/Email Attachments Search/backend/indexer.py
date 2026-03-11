import os
import sqlite3
from pdfminer.high_level import extract_text
from dotenv import load_dotenv

# Load configuration
load_dotenv()
# allow overriding via environment; fall back to a sensible default
PDF_FOLDER = os.getenv("PDF_FOLDER") or os.path.expanduser(
    "~/Library/CloudStorage/Dropbox/Email Attachments Search/Email Attachments"
)


def scan_pdfs(folder, progress_callback=None, existing_index=None, db_conn=None):
    """Recursively scan folder for PDF files and extract text.

    If `progress_callback` is provided it will be called for each file with
    the signature: progress_callback(absolute_path, index, total, skipped=False)

    Incremental mode — two supported sources for mtime cache (mutually exclusive;
    db_conn takes priority when both are supplied):

      db_conn       — sqlite3.Connection: mtime cache is loaded from the DB via
                      SELECT relative_path, mtime FROM documents.  This is the
                      preferred path once the DB migration is complete.

      existing_index — list of dicts from a previous in-memory index (legacy
                      path used by app.py until its reindex worker is updated in
                      Step 4).  Files whose mtime matches the stored value are
                      skipped.  Files that were deleted are dropped automatically.
    """
    # Build mtime cache: relative_path -> mtime (float)
    mtime_cache: dict[str, float] = {}

    if db_conn is not None:
        # DB path: load all stored mtimes in one query
        rows = db_conn.execute(
            "SELECT relative_path, mtime FROM documents WHERE mtime IS NOT NULL"
        ).fetchall()
        mtime_cache = {row[0]: row[1] for row in rows}
    elif existing_index:
        # Legacy dict path: keyed by absolute path for backward compat
        for doc in existing_index:
            if "path" in doc and "mtime" in doc and doc["mtime"] is not None:
                rel = doc.get("relative_path", "")
                if rel:
                    mtime_cache[rel] = doc["mtime"]

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

        # Skip unchanged files (mtime cache keyed by relative_path)
        if current_mtime is not None and mtime_cache.get(relative_path) == current_mtime:
            # Reuse stored text from DB if available, otherwise from existing_index
            if db_conn is not None:
                row = db_conn.execute(
                    "SELECT path, relative_path, filename, mtime, text FROM documents "
                    "WHERE relative_path = ?",
                    (relative_path,),
                ).fetchone()
                if row:
                    docs.append(dict(row))
                    if progress_callback:
                        try:
                            progress_callback(absolute_path, idx, total, skipped=True)
                        except Exception:
                            pass
                    continue
            else:
                # Legacy: find the cached doc in existing_index
                for cached_doc in (existing_index or []):
                    if cached_doc.get("relative_path") == relative_path:
                        docs.append(cached_doc)
                        if progress_callback:
                            try:
                                progress_callback(absolute_path, idx, total, skipped=True)
                            except Exception:
                                pass
                        break
                else:
                    pass  # not found in cache — fall through to extract
                # If we appended above, the for/else continue already happened;
                # check whether docs grew to decide if we should skip extraction.
                if docs and docs[-1].get("relative_path") == relative_path:
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


def save_index_to_db(conn: sqlite3.Connection, docs: list[dict],
                     incremental: bool = False) -> None:
    """Write indexed documents to the SQLite DB and keep FTS in sync.

    For a full scan (incremental=False):
      - Upserts every doc.
      - Prunes rows for files that are no longer on disk.
      - Rebuilds the FTS index from scratch for consistency.

    For an incremental scan (incremental=True):
      - Upserts only new/changed docs (unchanged ones were skipped by scan_pdfs).
      - Skips FTS rebuild — the INSERT/UPDATE triggers keep FTS in sync per row.
      - Does NOT prune stale rows (deleted files are pruned on the next full scan).
    """
    from backend.database import upsert_document, delete_missing_documents, fts_rebuild

    with conn:
        for doc in docs:
            upsert_document(
                conn,
                path=doc.get("path", ""),
                relative_path=doc.get("relative_path", ""),
                filename=doc.get("filename", ""),
                mtime=doc.get("mtime"),
                text=doc.get("text", ""),
            )

        if not incremental:
            found = {doc["relative_path"] for doc in docs if doc.get("relative_path")}
            pruned = delete_missing_documents(conn, found)
            if pruned:
                print(f"Pruned {pruned} stale document(s) from DB.")
            fts_rebuild(conn)

    print(f"Saved index to DB ({len(docs)} documents, incremental={incremental})")


if __name__ == "__main__":
    if not PDF_FOLDER or not os.path.isdir(PDF_FOLDER):
        print("PDF_FOLDER not configured or does not exist. Please set the PDF_FOLDER environment variable or update the default path.")
        exit(1)

    from backend.database import init_db, get_connection
    init_db()
    conn = get_connection()

    try:
        documents = scan_pdfs(PDF_FOLDER, db_conn=conn)
        save_index_to_db(conn, documents, incremental=False)
    finally:
        conn.close()
