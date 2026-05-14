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


def create_vector_db(progress_callback=None, incremental: bool = True) -> int:
    """Build/update FAISS vector DB from SQLite documents table using chunked embeddings.

    With incremental=True (default), skips documents already present in metadata.json
    and appends new chunks to the existing FAISS index — safe to resume after interruption.
    Returns the total number of chunks in the final index.
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

    # Load existing state for incremental mode
    existing_metadata: list[dict] = []
    existing_paths: set[str] = set()
    existing_index = None

    if incremental and os.path.exists(VECTOR_DB_FILE) and os.path.exists(METADATA_FILE):
        try:
            with open(METADATA_FILE, "r", encoding="utf-8") as f:
                existing_metadata = json.load(f)
            existing_index = faiss.read_index(VECTOR_DB_FILE)
            existing_paths = {m["path"] for m in existing_metadata}
        except Exception:
            # Corrupted files — fall back to full rebuild
            existing_metadata = []
            existing_paths = set()
            existing_index = None

    pending_rows = [r for r in rows if r["relative_path"] not in existing_paths]

    if not pending_rows:
        return len(existing_metadata)

    new_embeddings: list[list[float]] = []
    new_metadata: list[dict] = []

    for i, row in enumerate(pending_rows):
        text = row["text"] or ""
        if not text.strip():
            if progress_callback:
                progress_callback(row["filename"], i + 1, len(pending_rows))
            continue

        chunks = chunk_text(text)
        for chunk_idx, chunk in enumerate(chunks):
            embedding = get_embedding(chunk)
            if embedding:
                new_embeddings.append(embedding)
                new_metadata.append({
                    "path": row["relative_path"],
                    "filename": row["filename"],
                    "chunk_index": chunk_idx,
                    "snippet": chunk[:300],
                })

        if progress_callback:
            progress_callback(row["filename"], i + 1, len(pending_rows))

    if not new_embeddings:
        return len(existing_metadata)

    new_array = np.array(new_embeddings).astype("float32")

    if existing_index is not None:
        existing_index.add(new_array)
        final_index = existing_index
        final_metadata = existing_metadata + new_metadata
    else:
        dimension = new_array.shape[1]
        final_index = faiss.IndexFlatL2(dimension)
        final_index.add(new_array)
        final_metadata = new_metadata

    faiss.write_index(final_index, VECTOR_DB_FILE)
    with open(METADATA_FILE, "w", encoding="utf-8") as f:
        json.dump(final_metadata, f, indent=2)

    print(f"✅ Vector DB: {len(final_metadata)} total chunks ({len(new_metadata)} new from {len(pending_rows)} documents)")
    return len(final_metadata)


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
