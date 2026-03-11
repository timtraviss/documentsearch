"""
migrate.py — One-time migration of index.json + tags.json into SQLite.

Run once by hand after database.py is in place:

    source venv/bin/activate
    python backend/migrate.py

The script is idempotent: running it again will update existing rows rather
than duplicating them (upsert semantics).

index.json and tags.json are NOT deleted — they remain as a rollback option
until Step 5 of the migration plan.
"""

import os
import json
import sys

# Allow running as a script from the project root
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from backend.database import (
    init_db,
    get_connection,
    get_db_path,
    upsert_document,
    upsert_tag,
    fts_rebuild,
    get_document_count,
)
from dotenv import load_dotenv

load_dotenv()

INDEX_FILE = os.path.join(os.path.dirname(__file__), "index.json")
TAGS_FILE = os.path.join(
    os.path.expanduser("~/Library/Application Support/Document Search"),
    "tags.json",
)


def migrate_documents(conn, docs: list[dict]) -> tuple[int, int]:
    """Upsert all documents from index.json into the DB.

    Returns (inserted, updated) counts.
    """
    inserted = updated = 0
    for doc in docs:
        path = doc.get("path", "")
        relative_path = doc.get("relative_path", "")
        filename = doc.get("filename", "")
        text = doc.get("text", "")
        mtime = doc.get("mtime")  # None for all current docs — expected

        if not relative_path:
            print(f"  SKIP (no relative_path): {filename!r}")
            continue

        existing = conn.execute(
            "SELECT id FROM documents WHERE relative_path = ?", (relative_path,)
        ).fetchone()

        upsert_document(conn, path, relative_path, filename, mtime, text)

        if existing:
            updated += 1
        else:
            inserted += 1

    return inserted, updated


def migrate_tags(conn, tags: dict) -> tuple[int, int]:
    """Upsert all tags from tags.json into the DB.

    Returns (inserted, updated) counts.
    """
    inserted = updated = 0
    for relative_path, fields in tags.items():
        existing = conn.execute(
            "SELECT id FROM tags WHERE relative_path = ?", (relative_path,)
        ).fetchone()

        upsert_tag(conn, relative_path, fields)

        if existing:
            updated += 1
        else:
            inserted += 1

    return inserted, updated


def main():
    print("=== Document Search — SQLite Migration ===\n")
    print(f"DB path:    {get_db_path()}")
    print(f"index.json: {INDEX_FILE}")
    print(f"tags.json:  {TAGS_FILE}\n")

    # --- Initialise schema ---
    print("Initialising schema...")
    init_db()
    print("  Schema ready.\n")

    conn = get_connection()

    try:
        # --- Migrate documents ---
        if not os.path.exists(INDEX_FILE):
            print(f"WARNING: index.json not found at {INDEX_FILE} — skipping documents.")
            doc_inserted = doc_updated = 0
        else:
            with open(INDEX_FILE, "r", encoding="utf-8") as f:
                docs = json.load(f)
            print(f"Migrating {len(docs)} documents from index.json...")
            with conn:
                doc_inserted, doc_updated = migrate_documents(conn, docs)
            print(f"  Inserted: {doc_inserted}  Updated: {doc_updated}\n")

        # --- Migrate tags ---
        if not os.path.exists(TAGS_FILE):
            print(f"WARNING: tags.json not found at {TAGS_FILE} — skipping tags.")
            tag_inserted = tag_updated = 0
        else:
            with open(TAGS_FILE, "r", encoding="utf-8") as f:
                tags = json.load(f)
            print(f"Migrating {len(tags)} tag entries from tags.json...")
            with conn:
                tag_inserted, tag_updated = migrate_tags(conn, tags)
            print(f"  Inserted: {tag_inserted}  Updated: {tag_updated}\n")

        # --- Rebuild FTS index ---
        print("Rebuilding FTS5 index...")
        with conn:
            fts_rebuild(conn)
        print("  FTS rebuild complete.\n")

        # --- Summary ---
        total_docs = get_document_count(conn)
        total_tags = conn.execute("SELECT COUNT(*) FROM tags").fetchone()[0]
        print("=== Migration complete ===")
        print(f"  Documents in DB: {total_docs}")
        print(f"  Tags in DB:      {total_tags}")
        print(f"\nindex.json and tags.json have NOT been deleted.")
        print("They remain as a rollback option until Step 5 of the migration plan.")

    finally:
        conn.close()


if __name__ == "__main__":
    main()
