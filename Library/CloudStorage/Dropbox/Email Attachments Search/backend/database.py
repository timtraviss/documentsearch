"""
database.py — SQLite storage layer for Document Search.

Schema:
  documents      — one row per indexed file (path, text, mtime, etc.)
  documents_fts  — FTS5 virtual table backed by documents (full-text search)
  tags           — one row per tagged document (replaces tags.json)

The DB file lives in the Dropbox project folder so it is cloud-backed-up
automatically.  The path can be overridden via the DB_PATH env variable.

Thread safety: never share a Connection across threads.  Each Flask request
should call get_connection() (or use the g-based helper in app.py) to get
its own short-lived connection.  The reindex background thread does the same.
"""

import os
import json
import sqlite3
from dotenv import load_dotenv

load_dotenv()

# ---------------------------------------------------------------------------
# DB path
# ---------------------------------------------------------------------------

def get_db_path() -> str:
    """Return the absolute path to search.db.

    Priority:
      1. DB_PATH env variable (allows bundle / deployment overrides)
      2. Same directory as this file (i.e. backend/search.db), which lives
         inside the Dropbox project folder and is therefore cloud-backed-up.
    """
    env = os.getenv("DB_PATH")
    if env:
        return env
    return os.path.join(os.path.dirname(__file__), "search.db")


# ---------------------------------------------------------------------------
# Connection
# ---------------------------------------------------------------------------

def get_connection() -> sqlite3.Connection:
    """Open and return a new SQLite connection.

    Callers are responsible for closing it.  Do not store the returned
    connection in a module-level global — create one per thread/request.
    """
    path = get_db_path()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    conn = sqlite3.connect(path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    # WAL mode: allows concurrent readers while a writer is active (reindex
    # thread + Flask request threads coexist safely).
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA foreign_keys = ON")
    # Slightly relaxed durability for bulk writes (safe for non-critical data).
    conn.execute("PRAGMA synchronous = NORMAL")
    return conn


# ---------------------------------------------------------------------------
# Schema
# ---------------------------------------------------------------------------

_DDL = """
CREATE TABLE IF NOT EXISTS documents (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    path          TEXT NOT NULL UNIQUE,        -- absolute filesystem path
    relative_path TEXT NOT NULL UNIQUE,        -- path relative to PDF_FOLDER
    filename      TEXT NOT NULL,
    mtime         REAL,                        -- float epoch from os.path.getmtime
    text          TEXT NOT NULL DEFAULT '',    -- full extracted text
    snippet       TEXT GENERATED ALWAYS AS (substr(text, 1, 500)) VIRTUAL
);

CREATE INDEX IF NOT EXISTS idx_documents_relative_path
    ON documents(relative_path);

CREATE INDEX IF NOT EXISTS idx_documents_filename
    ON documents(filename);

-- FTS5 virtual table.  content=documents means FTS reads column values from
-- the documents table when doing integrity checks / rebuilds.
-- tokenize="unicode61 remove_diacritics 2" handles accented chars in names.
CREATE VIRTUAL TABLE IF NOT EXISTS documents_fts USING fts5(
    filename,
    text,
    content=documents,
    content_rowid=id,
    tokenize="unicode61 remove_diacritics 2"
);

-- Keep FTS in sync with documents via triggers.
CREATE TRIGGER IF NOT EXISTS documents_ai
AFTER INSERT ON documents BEGIN
    INSERT INTO documents_fts(rowid, filename, text)
    VALUES (new.id, new.filename, new.text);
END;

CREATE TRIGGER IF NOT EXISTS documents_ad
AFTER DELETE ON documents BEGIN
    INSERT INTO documents_fts(documents_fts, rowid, filename, text)
    VALUES ('delete', old.id, old.filename, old.text);
END;

CREATE TRIGGER IF NOT EXISTS documents_au
AFTER UPDATE ON documents BEGIN
    INSERT INTO documents_fts(documents_fts, rowid, filename, text)
    VALUES ('delete', old.id, old.filename, old.text);
    INSERT INTO documents_fts(rowid, filename, text)
    VALUES (new.id, new.filename, new.text);
END;

-- Tags table.  One row per document, keyed by relative_path (matches the
-- existing tags.json dict key format and the frontend's path param).
CREATE TABLE IF NOT EXISTS tags (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    relative_path  TEXT NOT NULL UNIQUE,
    type           TEXT NOT NULL DEFAULT '',
    company        TEXT NOT NULL DEFAULT '',
    year           TEXT NOT NULL DEFAULT '',
    amount         TEXT NOT NULL DEFAULT '',
    invoice_number TEXT NOT NULL DEFAULT '',
    status         TEXT NOT NULL DEFAULT '',
    extra_json     TEXT,                       -- JSON blob for unknown future fields
    updated_at     TEXT DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_tags_relative_path ON tags(relative_path);
CREATE INDEX IF NOT EXISTS idx_tags_type          ON tags(type);
CREATE INDEX IF NOT EXISTS idx_tags_company       ON tags(company);
CREATE INDEX IF NOT EXISTS idx_tags_year          ON tags(year);
"""


def init_db() -> None:
    """Create schema if it does not already exist.  Safe to call on every startup."""
    conn = get_connection()
    try:
        conn.executescript(_DDL)
        conn.commit()
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Document helpers
# ---------------------------------------------------------------------------

def upsert_document(conn: sqlite3.Connection,
                    path: str,
                    relative_path: str,
                    filename: str,
                    mtime: float | None,
                    text: str) -> None:
    """Insert or update a document row and keep FTS in sync.

    Uses an explicit SELECT + UPDATE/INSERT rather than INSERT OR REPLACE so
    that the row id is preserved on updates (INSERT OR REPLACE would assign a
    new id, orphaning the old FTS entry even with triggers in place).
    """
    row = conn.execute(
        "SELECT id FROM documents WHERE relative_path = ?", (relative_path,)
    ).fetchone()

    if row:
        conn.execute(
            """UPDATE documents
               SET path = ?, filename = ?, mtime = ?, text = ?
               WHERE relative_path = ?""",
            (path, filename, mtime, text, relative_path),
        )
    else:
        conn.execute(
            """INSERT INTO documents (path, relative_path, filename, mtime, text)
               VALUES (?, ?, ?, ?, ?)""",
            (path, relative_path, filename, mtime, text),
        )


def delete_missing_documents(conn: sqlite3.Connection,
                              found_relative_paths: set[str]) -> int:
    """Remove documents whose relative_path is no longer in the scanned set.

    Returns the number of rows deleted.
    """
    if not found_relative_paths:
        return 0
    existing = {
        row[0]
        for row in conn.execute("SELECT relative_path FROM documents").fetchall()
    }
    stale = existing - found_relative_paths
    if not stale:
        return 0
    placeholders = ",".join("?" * len(stale))
    conn.execute(
        f"DELETE FROM documents WHERE relative_path IN ({placeholders})",
        list(stale),
    )
    return len(stale)


def fts_rebuild(conn: sqlite3.Connection) -> None:
    """Rebuild the FTS5 index from the documents table.

    Run this after a bulk import or full reindex to ensure FTS is consistent.
    Takes milliseconds for thousands of documents.
    """
    conn.execute("INSERT INTO documents_fts(documents_fts) VALUES ('rebuild')")


def get_document_count(conn: sqlite3.Connection) -> int:
    return conn.execute("SELECT COUNT(*) FROM documents").fetchone()[0]


# ---------------------------------------------------------------------------
# Tag helpers
# ---------------------------------------------------------------------------

_KNOWN_TAG_FIELDS = {"type", "company", "year", "amount", "invoice_number", "status"}


def _split_tag_fields(fields: dict) -> tuple[dict, dict]:
    """Split a tag dict into known fields and extra (unknown) fields."""
    known = {k: str(v) for k, v in fields.items() if k in _KNOWN_TAG_FIELDS}
    extra = {k: v for k, v in fields.items() if k not in _KNOWN_TAG_FIELDS
             and k not in ("relative_path", "auto", "updated_at", "id")}
    return known, extra


def get_tag(conn: sqlite3.Connection, relative_path: str) -> dict | None:
    """Return the tag dict for a document, or None if not found.

    Unknown fields stored in extra_json are merged back into the result so
    the API response shape is backward-compatible with tags.json consumers.
    """
    row = conn.execute(
        "SELECT * FROM tags WHERE relative_path = ?", (relative_path,)
    ).fetchone()
    if not row:
        return None
    result = {
        "type": row["type"],
        "company": row["company"],
        "year": row["year"],
        "amount": row["amount"],
        "invoice_number": row["invoice_number"],
        "status": row["status"],
    }
    if row["extra_json"]:
        try:
            result.update(json.loads(row["extra_json"]))
        except (json.JSONDecodeError, TypeError):
            pass
    return result


def upsert_tag(conn: sqlite3.Connection,
               relative_path: str,
               fields: dict) -> None:
    """Insert or update a tag row for the given relative_path."""
    known, extra = _split_tag_fields(fields)
    extra_json = json.dumps(extra) if extra else None

    existing = conn.execute(
        "SELECT id FROM tags WHERE relative_path = ?", (relative_path,)
    ).fetchone()

    if existing:
        conn.execute(
            """UPDATE tags
               SET type = ?, company = ?, year = ?, amount = ?,
                   invoice_number = ?, status = ?, extra_json = ?,
                   updated_at = datetime('now')
               WHERE relative_path = ?""",
            (
                known.get("type", ""),
                known.get("company", ""),
                known.get("year", ""),
                known.get("amount", ""),
                known.get("invoice_number", ""),
                known.get("status", ""),
                extra_json,
                relative_path,
            ),
        )
    else:
        conn.execute(
            """INSERT INTO tags
               (relative_path, type, company, year, amount, invoice_number, status, extra_json)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                relative_path,
                known.get("type", ""),
                known.get("company", ""),
                known.get("year", ""),
                known.get("amount", ""),
                known.get("invoice_number", ""),
                known.get("status", ""),
                extra_json,
            ),
        )


def upsert_tags_bulk(conn: sqlite3.Connection,
                     updates: list[tuple[str, dict]]) -> int:
    """Upsert multiple tags in a single transaction.

    Each item in `updates` is a (relative_path, fields_dict) tuple.
    Returns the number of rows affected.
    """
    with conn:
        for relative_path, fields in updates:
            upsert_tag(conn, relative_path, fields)
    return len(updates)


def get_all_tags(conn: sqlite3.Connection) -> dict[str, dict]:
    """Return all tags as a dict keyed by relative_path.

    Matches the shape of the old tags.json so existing route logic can be
    swapped in gradually during the migration.
    """
    rows = conn.execute("SELECT * FROM tags").fetchall()
    result = {}
    for row in rows:
        tag = {
            "type": row["type"],
            "company": row["company"],
            "year": row["year"],
            "amount": row["amount"],
            "invoice_number": row["invoice_number"],
            "status": row["status"],
        }
        if row["extra_json"]:
            try:
                tag.update(json.loads(row["extra_json"]))
            except (json.JSONDecodeError, TypeError):
                pass
        result[row["relative_path"]] = tag
    return result
