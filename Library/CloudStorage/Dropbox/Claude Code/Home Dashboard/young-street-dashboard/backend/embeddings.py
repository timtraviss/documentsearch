import os
import json
import numpy as np

try:
    import faiss
    HAS_FAISS = True
except ImportError:
    HAS_FAISS = False

try:
    from openai import OpenAI
    HAS_OPENAI = True
except ImportError:
    HAS_OPENAI = False

FAISS_PATH    = os.path.join(os.path.dirname(__file__), 'house.faiss')
META_PATH     = os.path.join(os.path.dirname(__file__), 'house_metadata.json')
CHUNK_SIZE    = 1600
CHUNK_OVERLAP = 200
DIM           = 1536

_client = None


def _oai():
    global _client
    if _client is None:
        _client = OpenAI()
    return _client


def chunk_text(text, size=CHUNK_SIZE, overlap=CHUNK_OVERLAP):
    chunks = []
    start = 0
    while start < len(text):
        end = start + size
        chunks.append(text[start:end])
        # Only continue if there's more text beyond the overlap region
        if end >= len(text):
            break
        start += size - overlap
    return chunks


def get_embedding(text):
    resp = _oai().embeddings.create(
        model='text-embedding-3-small',
        input=text[:8191],
    )
    return resp.data[0].embedding


def build_embeddings(docs, progress_callback=None):
    """
    docs: list of {path, filename, name, text} dicts.
    Writes house.faiss + house_metadata.json.
    """
    if not HAS_FAISS or not HAS_OPENAI:
        raise RuntimeError('faiss-cpu and openai packages are required')

    vectors = []
    metadata = []

    for i, doc in enumerate(docs):
        if not doc.get('text'):
            continue
        if progress_callback:
            progress_callback(f'Embedding {i + 1}/{len(docs)}: {doc["filename"]}')
        chunks = chunk_text(doc['text'])
        for j, chunk in enumerate(chunks):
            emb = get_embedding(chunk)
            vectors.append(emb)
            metadata.append({
                'path':        doc['path'],
                'filename':    doc['filename'],
                'name':        doc.get('name') or doc['filename'],
                'chunk_index': j,
                'snippet':     chunk[:200],
            })

    if not vectors:
        if progress_callback:
            progress_callback('No text to embed — skipping FAISS build')
        return

    arr = np.array(vectors, dtype='float32')
    index = faiss.IndexFlatL2(DIM)
    index.add(arr)
    faiss.write_index(index, FAISS_PATH)
    with open(META_PATH, 'w') as f:
        json.dump(metadata, f)

    if progress_callback:
        progress_callback(f'FAISS index built: {len(vectors)} vectors')


def search_chunks(query, top_k=6):
    """Return list of metadata dicts for the top_k nearest chunks."""
    if not HAS_FAISS or not os.path.exists(FAISS_PATH):
        return []

    index = faiss.read_index(FAISS_PATH)
    with open(META_PATH) as f:
        metadata = json.load(f)

    emb = np.array([get_embedding(query)], dtype='float32')
    _, indices = index.search(emb, min(top_k, len(metadata)))
    return [metadata[i] for i in indices[0] if 0 <= i < len(metadata)]
