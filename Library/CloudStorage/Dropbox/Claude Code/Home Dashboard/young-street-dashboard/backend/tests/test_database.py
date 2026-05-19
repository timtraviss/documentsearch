import os
import tempfile
import pytest
import database


@pytest.fixture(autouse=True)
def tmp_db(tmp_path, monkeypatch):
    monkeypatch.setattr(database, 'DB_PATH', str(tmp_path / 'test.db'))
    yield


def test_init_db_creates_tables():
    database.init_db()
    conn = database.get_connection()
    tables = {r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'"
    )}
    conn.close()
    assert 'documents' in tables


def test_upsert_and_count():
    database.init_db()
    database.upsert_document('/tmp/a.pdf', 'a.pdf', 'Doc A', 1000.0, 'Some text')
    assert database.get_document_count() == 1


def test_upsert_is_idempotent():
    database.init_db()
    database.upsert_document('/tmp/a.pdf', 'a.pdf', 'Doc A', 1000.0, 'text v1')
    database.upsert_document('/tmp/a.pdf', 'a.pdf', 'Doc A', 2000.0, 'text v2')
    assert database.get_document_count() == 1
    docs = database.get_all_documents()
    assert docs[0]['mtime'] == 2000.0


def test_get_last_indexed():
    database.init_db()
    assert database.get_last_indexed() is None
    database.upsert_document('/tmp/b.pdf', 'b.pdf', 'Doc B', 1.0, 'text')
    assert database.get_last_indexed() is not None


def test_get_all_documents_with_text():
    database.init_db()
    database.upsert_document('/tmp/c.pdf', 'c.pdf', 'Doc C', 1.0, 'hello world')
    docs = database.get_all_documents_with_text()
    assert len(docs) == 1
    assert docs[0]['text'] == 'hello world'
