import json
import os
import numpy as np
import faiss
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

VECTOR_DB_FILE = os.path.join(os.path.dirname(__file__), "vector.faiss")
METADATA_FILE = os.path.join(os.path.dirname(__file__), "metadata.json")

CHUNK_SIZE = 1600
CHUNK_OVERLAP = 200

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def chunk_text(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list[str]:
    """Split text into overlapping fixed-size chunks."""
    if not text or not text.strip():
        return []
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunks.append(text[start:end])
        if end >= len(text):
            break
        start = end - overlap
    return chunks


def get_embedding(text: str, model: str = "text-embedding-3-small") -> list[float] | None:
    """Generate embedding via OpenAI."""
    if not text or not text.strip():
        return None
    response = client.embeddings.create(
        input=text[:8191],
        model=model,
    )
    return response.data[0].embedding


def create_vector_db(progress_callback=None) -> int:
    """Build FAISS vector DB from SQLite documents table using chunked embeddings.

    Returns the number of chunks embedded.
    Loads documents from search.db — run after a full re-index if documents change.
    """
    try:
        from backend.database import get_connection
    except ImportError:
        from database import get_connection  # when run directly from backend/

    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT relative_path, filename, text FROM documents"
        ).fetchall()
    finally:
        conn.close()

    embeddings: list[list[float]] = []
    metadata: list[dict] = []

    for i, row in enumerate(rows):
        text = row["text"] or ""
        if not text.strip():
            continue

        chunks = chunk_text(text)
        for chunk_idx, chunk in enumerate(chunks):
            embedding = get_embedding(chunk)
            if embedding:
                embeddings.append(embedding)
                metadata.append({
                    "path": row["relative_path"],
                    "filename": row["filename"],
                    "chunk_index": chunk_idx,
                    "snippet": chunk[:300],
                })

        if progress_callback:
            progress_callback(row["filename"], i + 1, len(rows))

    if not embeddings:
        print("No embeddings generated — is search.db populated?")
        return 0

    embeddings_array = np.array(embeddings).astype("float32")
    dimension = embeddings_array.shape[1]
    index = faiss.IndexFlatL2(dimension)
    index.add(embeddings_array)

    faiss.write_index(index, VECTOR_DB_FILE)
    with open(METADATA_FILE, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2)

    print(f"✅ Vector DB: {len(metadata)} chunks from {len(rows)} documents")
    return len(metadata)


def search_chunks(query: str, top_k: int = 6) -> list[dict]:
    """Search FAISS index, returning raw chunk matches (may include multiple chunks per PDF).

    Used by /ask to provide document context to Claude.
    """
    if not os.path.exists(VECTOR_DB_FILE):
        return []

    query_embedding = get_embedding(query)
    if not query_embedding:
        return []

    index = faiss.read_index(VECTOR_DB_FILE)
    with open(METADATA_FILE, "r", encoding="utf-8") as f:
        metadata = json.load(f)

    k = min(top_k, len(metadata))
    query_vector = np.array([query_embedding]).astype("float32")
    _, indices = index.search(query_vector, k)

    return [metadata[i] for i in indices[0] if 0 <= i < len(metadata)]


def search(query: str, top_k: int = 6) -> list[dict]:
    """Semantic search returning deduplicated doc entries (one per PDF).

    Used by the existing /search endpoint.
    """
    chunks = search_chunks(query, top_k=top_k * 2)
    seen: set[str] = set()
    results: list[dict] = []
    for c in chunks:
        path = c["path"]
        if path not in seen:
            seen.add(path)
            results.append(c)
            if len(results) >= top_k:
                break
    return results


if __name__ == "__main__":
    if not os.getenv("OPENAI_API_KEY"):
        print("❌ OPENAI_API_KEY not set")
        exit(1)
    create_vector_db()
