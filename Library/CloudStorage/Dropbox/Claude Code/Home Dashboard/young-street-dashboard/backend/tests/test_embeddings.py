import pytest
import embeddings


def test_chunk_text_single_chunk():
    text = 'x' * 1000
    chunks = embeddings.chunk_text(text)
    assert len(chunks) == 1
    assert chunks[0] == text


def test_chunk_text_multiple_chunks():
    text = 'a' * 2000
    chunks = embeddings.chunk_text(text)
    assert len(chunks) == 2
    assert len(chunks[0]) == 1600
    assert len(chunks[1]) == 600   # text[1400:2000]


def test_chunk_text_overlap():
    text = 'ab' * 1000   # 2000 chars
    chunks = embeddings.chunk_text(text)
    # Overlap region: chunks[0][1400:1600] == chunks[1][:200]
    assert chunks[0][1400:1600] == chunks[1][:200]


def test_chunk_text_exact_size():
    text = 'x' * 1600
    chunks = embeddings.chunk_text(text)
    assert len(chunks) == 1


def test_search_chunks_returns_empty_without_index(tmp_path, monkeypatch):
    monkeypatch.setattr(embeddings, 'FAISS_PATH', str(tmp_path / 'missing.faiss'))
    result = embeddings.search_chunks('any query')
    assert result == []
