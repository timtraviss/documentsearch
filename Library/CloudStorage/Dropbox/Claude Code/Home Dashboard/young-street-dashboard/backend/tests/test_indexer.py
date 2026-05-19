import os
import tempfile
import pytest
import database
import indexer


@pytest.fixture(autouse=True)
def tmp_db(tmp_path, monkeypatch):
    monkeypatch.setattr(database, 'DB_PATH', str(tmp_path / 'test.db'))
    database.init_db()
    yield


def test_scan_empty_folder(tmp_path):
    indexed, skipped = indexer.scan_pdfs(str(tmp_path))
    assert indexed == 0
    assert skipped == 0


def test_scan_skips_unchanged(tmp_path, monkeypatch):
    # Create a fake PDF that pdfminer can read
    pdf = tmp_path / 'test.pdf'
    pdf.write_bytes(b'%PDF-1.4 fake')
    mtime = os.path.getmtime(str(pdf))

    # Pre-populate db with same path and mtime
    database.upsert_document(str(pdf), 'test.pdf', 'test', mtime, 'cached text')

    # Patch extract_text to ensure it's not called
    called = []
    monkeypatch.setattr('indexer.extract_text', lambda p: called.append(p) or '')

    indexed, skipped = indexer.scan_pdfs(str(tmp_path))
    assert indexed == 0
    assert skipped == 1
    assert called == []  # extraction was skipped


def test_scan_indexes_new_file(tmp_path, monkeypatch):
    pdf = tmp_path / 'report.pdf'
    pdf.write_bytes(b'%PDF-1.4 fake')

    monkeypatch.setattr('indexer.extract_text', lambda p: 'extracted content')

    indexed, skipped = indexer.scan_pdfs(str(tmp_path))
    assert indexed == 1
    assert skipped == 0
    assert database.get_document_count() == 1
