import pytest
from backend.embeddings import chunk_text


def test_chunk_text_short_text():
    chunks = chunk_text("hello world", chunk_size=1600, overlap=200)
    assert chunks == ["hello world"]


def test_chunk_text_empty():
    assert chunk_text("") == []
    assert chunk_text("   ") == []


def test_chunk_text_exact_size():
    text = "a" * 1600
    chunks = chunk_text(text, chunk_size=1600, overlap=200)
    assert chunks == [text]


def test_chunk_text_splits_with_overlap():
    # text of 10 chars, chunk_size=6, overlap=2
    # chunk 0: [0:6]   = "abcdef"
    # chunk 1: [4:10]  = "efghij"  (start = 6-2 = 4)
    text = "abcdefghij"
    chunks = chunk_text(text, chunk_size=6, overlap=2)
    assert chunks == ["abcdef", "efghij"]


def test_chunk_text_three_chunks():
    # text of 2000 chars, chunk_size=1600, overlap=200
    # chunk 0: [0:1600]
    # chunk 1: [1400:2000]  (start = 1600-200 = 1400)
    text = "a" * 2000
    chunks = chunk_text(text, chunk_size=1600, overlap=200)
    assert len(chunks) == 2
    assert len(chunks[0]) == 1600
    assert len(chunks[1]) == 600
