import os
import sqlite3
from datetime import datetime, timezone

DB_PATH = os.path.join(os.path.dirname(__file__), 'house.db')


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute('PRAGMA journal_mode=WAL')
    return conn


def init_db():
    conn = get_connection()
    try:
        conn.executescript('''
            CREATE TABLE IF NOT EXISTS documents (
                id         INTEGER PRIMARY KEY,
                path       TEXT UNIQUE NOT NULL,
                filename   TEXT NOT NULL,
                name       TEXT,
                mtime      REAL NOT NULL,
                text       TEXT,
                snippet    TEXT,
                indexed_at TEXT
            );
            CREATE VIRTUAL TABLE IF NOT EXISTS documents_fts
                USING fts5(
                    text,
                    content='documents',
                    content_rowid='id',
                    tokenize='unicode61 remove_diacritics 2'
                );
        ''')
        conn.commit()
    finally:
        conn.close()


def upsert_document(path, filename, name, mtime, text):
    snippet = (text or '')[:200]
    indexed_at = datetime.now(timezone.utc).isoformat()
    conn = get_connection()
    try:
        conn.execute('''
            INSERT INTO documents (path, filename, name, mtime, text, snippet, indexed_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(path) DO UPDATE SET
                filename   = excluded.filename,
                name       = excluded.name,
                mtime      = excluded.mtime,
                text       = excluded.text,
                snippet    = excluded.snippet,
                indexed_at = excluded.indexed_at
        ''', (path, filename, name, mtime, text, snippet, indexed_at))
        conn.commit()
    finally:
        conn.close()


def get_document_count():
    conn = get_connection()
    try:
        count = conn.execute('SELECT COUNT(*) FROM documents').fetchone()[0]
        return count
    finally:
        conn.close()


def get_last_indexed():
    conn = get_connection()
    try:
        row = conn.execute('SELECT MAX(indexed_at) FROM documents').fetchone()
        return row[0] if row else None
    finally:
        conn.close()


def get_all_documents():
    conn = get_connection()
    try:
        rows = conn.execute(
            'SELECT path, filename, name, mtime FROM documents'
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def get_all_documents_with_text():
    conn = get_connection()
    try:
        rows = conn.execute(
            'SELECT path, filename, name, text FROM documents'
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()
