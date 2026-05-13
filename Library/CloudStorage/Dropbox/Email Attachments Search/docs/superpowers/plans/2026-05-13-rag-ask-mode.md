# RAG Ask Mode Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a conversational "Ask AI" mode to the Document Search app — chunked embeddings for better retrieval, a `/ask` endpoint powered by Claude, and an `AskPanel` UI with full source cards and follow-up support.

**Architecture:** Rewrite `embeddings.py` to chunk documents before embedding and load from SQLite (not the stale `index.json`). Add `/ask` (Claude synthesis) and `/rebuild-embeddings` (background re-embed) endpoints to Flask. Wire a new `AskPanel` component into the React frontend behind a `SegmentedControl` mode toggle in `SearchBar`.

**Tech Stack:** Python/Flask backend, `anthropic` SDK (claude-sonnet-4-6), `openai` SDK (text-embedding-3-small embeddings), FAISS, React 18 + TypeScript, Mantine v7, `pdfjs-dist`.

---

## File Map

| File | Action | Responsibility |
|------|--------|----------------|
| `setup.py` | Modify | Add `anthropic` to py2app packages list |
| `backend/embeddings.py` | Rewrite | chunk_text, create_vector_db (SQLite source), search, search_chunks |
| `backend/app.py` | Modify | Add `/ask`, `/rebuild-embeddings`, `/rebuild-embeddings/status`; import search_chunks |
| `tests/test_embeddings.py` | Create | Tests for chunk_text |
| `tests/test_ask.py` | Create | Tests for /ask and /rebuild-embeddings endpoints |
| `frontend/src/types.ts` | Modify | Add AskMessage, AskSource, AskResponse, RebuildEmbeddingsStatus, AppMode |
| `frontend/src/api.ts` | Modify | Add ask(), startRebuildEmbeddings(), getRebuildEmbeddingsStatus() |
| `frontend/src/components/SearchBar.tsx` | Modify | Add SegmentedControl mode toggle; hide text input in Ask mode |
| `frontend/src/components/AskPanel.tsx` | Create | Chat history, source ResultCards, follow-up input, New chat |
| `frontend/src/App.tsx` | Modify | Add searchMode + askMessages state; render AskPanel |
| `frontend/src/components/ReindexModal.tsx` | Modify | Add Rebuild Embeddings section with log stream |

---

## Task 1: Add anthropic to setup.py py2app packages

**Files:**
- Modify: `setup.py`

- [ ] **Step 1: Add `anthropic` to the packages list**

In `setup.py`, the `OPTIONS` dict has a `'packages'` list. Add `'anthropic'` to it:

```python
'packages': [
    'backend',
    'flask',
    'pdfminer',
    'dotenv',
    'jinja2',
    'charset_normalizer',
    'cffi',
    'webview',
    'anthropic',        # ← add this line
],
```

- [ ] **Step 2: Verify the file parses correctly**

```bash
cd "/Users/timothytraviss/Library/CloudStorage/Dropbox/Email Attachments Search"
python -c "import ast; ast.parse(open('setup.py').read()); print('OK')"
```
Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add setup.py
git commit -m "build: add anthropic to py2app packages list"
```

---

## Task 2: chunk_text — TDD

**Files:**
- Create: `tests/test_embeddings.py`
- Modify: `backend/embeddings.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_embeddings.py`:

```python
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
```

- [ ] **Step 2: Run tests to confirm FAIL**

```bash
cd "/Users/timothytraviss/Library/CloudStorage/Dropbox/Email Attachments Search"
source venv/bin/activate
pytest tests/test_embeddings.py -v
```
Expected: `ImportError` or `AttributeError` — `chunk_text` not yet defined.

- [ ] **Step 3: Add chunk_text to embeddings.py**

Open `backend/embeddings.py`. Add the following at the top of the file, after the existing imports and constants, before `get_embedding`:

```python
CHUNK_SIZE = 1600
CHUNK_OVERLAP = 200


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
```

- [ ] **Step 4: Run tests to confirm PASS**

```bash
pytest tests/test_embeddings.py -v
```
Expected: all 5 tests `PASSED`.

- [ ] **Step 5: Commit**

```bash
git add tests/test_embeddings.py backend/embeddings.py
git commit -m "feat: add chunk_text helper to embeddings.py"
```

---

## Task 3: Rewrite embeddings.py — SQLite source, search, search_chunks

**Files:**
- Modify: `backend/embeddings.py`

This task fully replaces `create_vector_db()` (loads from SQLite instead of the stale `index.json`) and adds `search_chunks()`. The existing `search()` is updated to deduplicate by path.

- [ ] **Step 1: Replace the full contents of backend/embeddings.py**

```python
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
```

- [ ] **Step 2: Run existing chunk_text tests to confirm still passing**

```bash
pytest tests/test_embeddings.py -v
```
Expected: all 5 tests `PASSED`.

- [ ] **Step 3: Verify imports are correct**

```bash
source venv/bin/activate
python -c "from backend.embeddings import chunk_text, search, search_chunks, create_vector_db; print('OK')"
```
Expected: `OK`

- [ ] **Step 4: Commit**

```bash
git add backend/embeddings.py
git commit -m "feat: rewrite embeddings — chunk-based FAISS, SQLite source, search_chunks"
```

---

## Task 4: Add /ask endpoint to app.py — TDD

**Files:**
- Create: `tests/test_ask.py`
- Modify: `backend/app.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_ask.py`:

```python
import os
import pytest
from unittest.mock import patch, MagicMock


@pytest.fixture
def client():
    os.environ.setdefault("PDF_FOLDER", "/tmp")
    os.environ.setdefault("DB_PATH", os.path.join(
        os.path.dirname(__file__), "..", "backend", "search.db"
    ))
    import backend.app as app_module
    app_module.app.config["TESTING"] = True
    with app_module.app.test_client() as c:
        yield c


def test_ask_empty_query(client):
    res = client.post("/ask",
                      data='{"query": ""}',
                      content_type="application/json")
    assert res.status_code == 400
    assert "error" in res.get_json()


def test_ask_no_embeddings(client):
    import backend.app as app_module
    with patch.object(app_module, "HAS_EMBEDDINGS", False):
        res = client.post("/ask",
                          data='{"query": "test"}',
                          content_type="application/json")
    assert res.status_code == 503
    data = res.get_json()
    assert "error" in data
    assert "embeddings" in data["error"].lower()


def test_ask_missing_api_key(client):
    import backend.app as app_module
    mock_chunks = [{"path": "test.pdf", "filename": "test.pdf", "snippet": "some text"}]
    with patch.object(app_module, "HAS_EMBEDDINGS", True), \
         patch.object(app_module, "search_chunks", return_value=mock_chunks), \
         patch.dict(os.environ, {"ANTHROPIC_API_KEY": ""}):
        res = client.post("/ask",
                          data='{"query": "test"}',
                          content_type="application/json")
    assert res.status_code == 503


def test_ask_returns_answer_and_sources(client):
    import backend.app as app_module
    mock_chunks = [
        {"path": "contract.pdf", "filename": "contract.pdf",
         "snippet": "The notice period is 90 days."},
        {"path": "contract.pdf", "filename": "contract.pdf",
         "snippet": "Liability is capped at 3 months fees."},
    ]
    mock_response = MagicMock()
    mock_response.content = [MagicMock(text="The notice period is 90 days.")]

    with patch.object(app_module, "HAS_EMBEDDINGS", True), \
         patch.object(app_module, "search_chunks", return_value=mock_chunks), \
         patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"}), \
         patch("anthropic.Anthropic") as mock_cls:
        mock_cls.return_value.messages.create.return_value = mock_response
        res = client.post(
            "/ask",
            data='{"query": "What is the notice period?", "messages": []}',
            content_type="application/json",
        )

    assert res.status_code == 200
    data = res.get_json()
    assert data["answer"] == "The notice period is 90 days."
    # Two chunks from same doc → one deduplicated source
    assert len(data["sources"]) == 1
    assert data["sources"][0]["filename"] == "contract.pdf"


def test_ask_passes_conversation_history(client):
    import backend.app as app_module
    mock_chunks = [{"path": "a.pdf", "filename": "a.pdf", "snippet": "context"}]
    mock_response = MagicMock()
    mock_response.content = [MagicMock(text="Follow-up answer.")]

    history = [
        {"role": "user", "content": "First question"},
        {"role": "assistant", "content": "First answer"},
    ]

    with patch.object(app_module, "HAS_EMBEDDINGS", True), \
         patch.object(app_module, "search_chunks", return_value=mock_chunks), \
         patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"}), \
         patch("anthropic.Anthropic") as mock_cls:
        mock_cls.return_value.messages.create.return_value = mock_response
        res = client.post(
            "/ask",
            data=f'{{"query": "follow up", "messages": {__import__("json").dumps(history)}}}',
            content_type="application/json",
        )

    assert res.status_code == 200
    # Verify history was passed to Claude — messages should include history + new user turn
    call_kwargs = mock_cls.return_value.messages.create.call_args[1]
    messages_sent = call_kwargs["messages"]
    assert messages_sent[0]["role"] == "user"
    assert messages_sent[0]["content"] == "First question"
    assert messages_sent[1]["role"] == "assistant"
    assert messages_sent[-1]["role"] == "user"
```

- [ ] **Step 2: Run tests to confirm FAIL**

```bash
cd "/Users/timothytraviss/Library/CloudStorage/Dropbox/Email Attachments Search"
source venv/bin/activate
pytest tests/test_ask.py -v
```
Expected: `404` errors or `AttributeError` — `/ask` endpoint not yet defined.

- [ ] **Step 3: Update the embeddings import block at the top of app.py**

Find the existing block (around line 71–77):
```python
try:
    from embeddings import search as semantic_search
    HAS_EMBEDDINGS = os.path.exists(
        os.path.join(os.path.dirname(__file__), "vector.faiss")
    )
except ImportError:
    HAS_EMBEDDINGS = False
```

Replace it with:
```python
try:
    from embeddings import search as semantic_search, search_chunks
    HAS_EMBEDDINGS = os.path.exists(
        os.path.join(os.path.dirname(__file__), "vector.faiss")
    )
except ImportError:
    HAS_EMBEDDINGS = False
    search_chunks = None
```

- [ ] **Step 4: Add the /ask endpoint to app.py**

Add this block after the `/search` route (after line 413, before `@app.route("/reindex")`):

```python
@app.route("/ask", methods=["POST"])
def ask():
    """Conversational question-answering over indexed PDFs using Claude."""
    data = request.get_json(force=True) or {}
    query = (data.get("query") or "").strip()
    messages = data.get("messages") or []

    if not query:
        return jsonify({"error": "query is required"}), 400

    if not HAS_EMBEDDINGS:
        return jsonify({
            "error": "Embeddings not built. Rebuild embeddings from Tools → Re-index."
        }), 503

    anthropic_key = os.getenv("ANTHROPIC_API_KEY", "").strip()
    if not anthropic_key:
        return jsonify({"error": "ANTHROPIC_API_KEY not set in .env"}), 503

    try:
        chunks = search_chunks(query, top_k=6)
    except Exception as e:
        return jsonify({"error": f"Embedding search failed: {e}"}), 500

    if not chunks:
        return jsonify({
            "answer": "I couldn't find any relevant document excerpts for that question.",
            "sources": [],
        })

    # Build context string from chunks
    context_parts = [
        f"[Source: {c['filename']}]\n{c['snippet']}" for c in chunks
    ]
    context = "\n---\n".join(context_parts)

    # Deduplicate sources list (one entry per PDF path)
    seen_paths: set[str] = set()
    sources = []
    for c in chunks:
        if c["path"] not in seen_paths:
            seen_paths.add(c["path"])
            sources.append({
                "filename": c["filename"],
                "path": c["path"],
                "snippet": c["snippet"],
            })

    # Build Anthropic messages — history + new user turn with context
    anthropic_messages = []
    for msg in messages:
        role = msg.get("role")
        content = msg.get("content", "")
        if role in ("user", "assistant") and content:
            anthropic_messages.append({"role": role, "content": content})

    user_content = (
        f"Here are the relevant document excerpts:\n---\n{context}\n---\n\n"
        f"Question: {query}"
    )
    anthropic_messages.append({"role": "user", "content": user_content})

    try:
        import anthropic as anthropic_sdk
        ant_client = anthropic_sdk.Anthropic(api_key=anthropic_key)
        response = ant_client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=1024,
            system=(
                "You are a document assistant. Answer questions based only on the "
                "document excerpts provided. Cite documents by filename when relevant. "
                "If the answer is not in the provided excerpts, say so clearly."
            ),
            messages=anthropic_messages,
        )
        answer = response.content[0].text
    except Exception as e:
        return jsonify({"error": f"AI service unavailable: {e}"}), 500

    return jsonify({"answer": answer, "sources": sources})
```

- [ ] **Step 5: Run tests to confirm PASS**

```bash
pytest tests/test_ask.py -v
```
Expected: all 5 tests `PASSED`.

- [ ] **Step 6: Commit**

```bash
git add backend/app.py tests/test_ask.py
git commit -m "feat: add /ask endpoint — Claude synthesis over FAISS chunks"
```

---

## Task 5: Add /rebuild-embeddings endpoints to app.py — TDD

**Files:**
- Modify: `tests/test_ask.py`
- Modify: `backend/app.py`

- [ ] **Step 1: Add rebuild-embeddings tests to tests/test_ask.py**

Append to `tests/test_ask.py`:

```python
def test_rebuild_embeddings_starts(client):
    import backend.app as app_module
    app_module.rebuild_status["running"] = False
    res = client.post("/rebuild-embeddings", content_type="application/json")
    assert res.status_code == 200
    assert res.get_json()["status"] == "ok"
    # Give thread a moment to start, then reset state for test isolation
    import time; time.sleep(0.05)
    app_module.rebuild_status["running"] = False


def test_rebuild_embeddings_already_running(client):
    import backend.app as app_module
    app_module.rebuild_status["running"] = True
    try:
        res = client.post("/rebuild-embeddings", content_type="application/json")
        assert res.status_code == 409
    finally:
        app_module.rebuild_status["running"] = False


def test_rebuild_embeddings_status_shape(client):
    res = client.get("/rebuild-embeddings/status")
    assert res.status_code == 200
    data = res.get_json()
    assert "running" in data
    assert "logs" in data
    assert "count" in data
    assert "error" in data
```

- [ ] **Step 2: Run new tests to confirm FAIL**

```bash
pytest tests/test_ask.py::test_rebuild_embeddings_starts \
       tests/test_ask.py::test_rebuild_embeddings_already_running \
       tests/test_ask.py::test_rebuild_embeddings_status_shape -v
```
Expected: `404` — endpoint not yet defined.

- [ ] **Step 3: Add rebuild_status dict and endpoints to app.py**

After the `file_status` dict (around line 98), add:

```python
rebuild_status: dict = {
    "running": False,
    "logs": [],
    "count": 0,
    "error": None,
}
```

After the `/rebuild-embeddings` endpoint goes after the existing `/reindex/status` route. Add this block:

```python
@app.route("/rebuild-embeddings", methods=["POST"])
def rebuild_embeddings_route():
    """Start a background job to re-embed all documents into vector.faiss."""
    if rebuild_status["running"]:
        return jsonify({"status": "error", "error": "already running"}), 409

    def _log(msg: str) -> None:
        rebuild_status["logs"].append(msg)

    def worker() -> None:
        try:
            rebuild_status["running"] = True
            rebuild_status["logs"] = []
            rebuild_status["count"] = 0
            rebuild_status["error"] = None
            _log("Starting embedding rebuild...")

            from embeddings import create_vector_db

            def progress_cb(filename: str, idx: int, total: int) -> None:
                _log(f"Embedding ({idx}/{total}): {filename}")

            count = create_vector_db(progress_callback=progress_cb)
            rebuild_status["count"] = count
            _log(f"Done. {count} chunks embedded.")
        except Exception as e:
            rebuild_status["error"] = str(e)
            _log(f"Error: {e}")
        finally:
            rebuild_status["running"] = False

    threading.Thread(target=worker, daemon=True).start()
    return jsonify({"status": "ok"})


@app.route("/rebuild-embeddings/status")
def rebuild_embeddings_status_api():
    return jsonify({
        "running": rebuild_status.get("running", False),
        "logs": rebuild_status.get("logs", [])[-200:],
        "count": rebuild_status.get("count", 0),
        "error": rebuild_status.get("error"),
    })
```

- [ ] **Step 4: Run all tests to confirm PASS**

```bash
pytest tests/test_ask.py -v
```
Expected: all 8 tests `PASSED`.

- [ ] **Step 5: Commit**

```bash
git add backend/app.py tests/test_ask.py
git commit -m "feat: add /rebuild-embeddings endpoint with background thread + status polling"
```

---

## Task 6: Add types — types.ts

**Files:**
- Modify: `frontend/src/types.ts`

- [ ] **Step 1: Append new types to frontend/src/types.ts**

Add at the end of `frontend/src/types.ts`:

```typescript
export type AppMode = 'search' | 'ask'

export interface AskSource {
  filename: string
  path: string
  snippet: string
}

export interface AskMessage {
  role: 'user' | 'assistant'
  content: string
  sources?: AskSource[]
}

export interface AskResponse {
  answer?: string
  sources?: AskSource[]
  error?: string
}

export interface RebuildEmbeddingsStatus {
  running: boolean
  logs: string[]
  count: number
  error: string | null
}
```

- [ ] **Step 2: Verify TypeScript compiles**

```bash
cd "/Users/timothytraviss/Library/CloudStorage/Dropbox/Email Attachments Search/frontend"
npx tsc --noEmit
```
Expected: no errors.

- [ ] **Step 3: Commit**

```bash
cd ..
git add frontend/src/types.ts
git commit -m "feat: add AskMessage, AskSource, AskResponse, AppMode types"
```

---

## Task 7: Add API functions — api.ts

**Files:**
- Modify: `frontend/src/api.ts`

- [ ] **Step 1: Add three new exports to frontend/src/api.ts**

Add at the end of `frontend/src/api.ts` (before the final closing):

```typescript
import type { AskMessage, AskResponse, RebuildEmbeddingsStatus } from './types'

export async function ask(query: string, messages: AskMessage[]): Promise<AskResponse> {
  const res = await fetch('/ask', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ query, messages }),
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({}))
    return { error: (err as { error?: string }).error ?? `Request failed: ${res.status}` }
  }
  return res.json()
}

export async function startRebuildEmbeddings(): Promise<void> {
  const res = await fetch('/rebuild-embeddings', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
  })
  if (!res.ok) throw new Error('Rebuild embeddings failed')
}

export async function getRebuildEmbeddingsStatus(): Promise<RebuildEmbeddingsStatus> {
  const res = await fetch('/rebuild-embeddings/status')
  if (!res.ok) throw new Error('Rebuild embeddings status failed')
  return res.json()
}
```

**Note:** The `import` statement for the new types must go at the top of the file alongside the existing import. Move it there — replace the existing first line:

```typescript
import type { SearchFilters, SearchResponse, DocumentTags, Stats, TagValues, ReindexStatus, FilePdfsStatus, StatsBreakdown } from './types'
```

with:

```typescript
import type { SearchFilters, SearchResponse, DocumentTags, Stats, TagValues, ReindexStatus, FilePdfsStatus, StatsBreakdown, AskMessage, AskResponse, RebuildEmbeddingsStatus } from './types'
```

(Remove the duplicate `import type` added at the bottom.)

- [ ] **Step 2: Verify TypeScript compiles**

```bash
cd "/Users/timothytraviss/Library/CloudStorage/Dropbox/Email Attachments Search/frontend"
npx tsc --noEmit
```
Expected: no errors.

- [ ] **Step 3: Commit**

```bash
cd ..
git add frontend/src/api.ts
git commit -m "feat: add ask, startRebuildEmbeddings, getRebuildEmbeddingsStatus to api.ts"
```

---

## Task 8: Mode toggle — SearchBar.tsx

**Files:**
- Modify: `frontend/src/components/SearchBar.tsx`

- [ ] **Step 1: Add AppMode import and new props to SearchBar.tsx**

Add `SegmentedControl` to the Mantine import (line 2) and `AppMode` to the types import (line 23):

```typescript
import {
  Box,
  Button,
  Checkbox,
  Collapse,
  Group,
  Menu,
  SegmentedControl,
  Select,
  SimpleGrid,
  TextInput,
} from '@mantine/core'
```

```typescript
import type { AppMode, SearchFilters } from '../types'
```

- [ ] **Step 2: Add appMode and onModeChange to the Props interface**

Replace the existing `interface Props {` block (lines 43–56) with:

```typescript
interface Props {
  filters: SearchFilters
  tagYears: string[]
  companies: string[]
  resultCount: number | null
  isIndexing: boolean
  appMode: AppMode
  onModeChange: (mode: AppMode) => void
  onSearch: (filters: SearchFilters) => void
  onClear: () => void
  onExportCsv: () => void
  onOpenReindex: () => void
  onOpenTagMgmt: () => void
  onOpenStats: () => void
  onOpenFilePdfs: () => void
}
```

- [ ] **Step 3: Update the function signature and return value**

Add `appMode` and `onModeChange` to the destructured props:

```typescript
export default function SearchBar({
  filters,
  tagYears,
  companies,
  resultCount,
  isIndexing,
  appMode,
  onModeChange,
  onSearch,
  onClear,
  onExportCsv,
  onOpenReindex,
  onOpenTagMgmt,
  onOpenStats,
  onOpenFilePdfs,
}: Props) {
```

Replace the return statement — wrap existing `<Box component="form" ...>` in a fragment with the SegmentedControl above it, and hide the form when in Ask mode:

```typescript
  return (
    <Box>
      <SegmentedControl
        value={appMode}
        onChange={(v) => onModeChange(v as AppMode)}
        data={[
          { value: 'search', label: 'Search documents' },
          { value: 'ask', label: 'Ask AI' },
        ]}
        mb="sm"
        color="teal"
        styles={{ root: { background: 'var(--card-bg)', border: '1px solid var(--border)' } }}
      />

      {appMode === 'search' && (
        <Box component="form" onSubmit={handleSubmit}>
          {/* existing content — Main search row, Advanced filters, Results header */}
          ...
        </Box>
      )}
    </Box>
  )
```

The full content inside `<Box component="form" onSubmit={handleSubmit}>` is unchanged — keep the `{/* Main search row */}` Group, the `{/* Advanced filters */}` Collapse, and the `{/* Results header */}` Group exactly as they are. Only the outer structure changes: the `<Box component="form">` is now wrapped in a conditional and the new `<Box>` + `SegmentedControl` are added above it.

- [ ] **Step 4: Verify TypeScript compiles**

```bash
cd "/Users/timothytraviss/Library/CloudStorage/Dropbox/Email Attachments Search/frontend"
npx tsc --noEmit
```
Expected: errors only about `appMode`/`onModeChange` not yet passed from App.tsx (fixed in Task 10). No structural errors.

- [ ] **Step 5: Commit**

```bash
cd ..
git add frontend/src/components/SearchBar.tsx
git commit -m "feat: add Search/Ask mode toggle to SearchBar"
```

---

## Task 9: Create AskPanel.tsx

**Files:**
- Create: `frontend/src/components/AskPanel.tsx`

- [ ] **Step 1: Create the file**

Create `frontend/src/components/AskPanel.tsx`:

```typescript
import { useEffect, useRef, useState } from 'react'
import {
  Badge,
  Box,
  Button,
  Group,
  SimpleGrid,
  Text,
  TextInput,
} from '@mantine/core'
import { IconRefresh, IconSend } from '@tabler/icons-react'
import ResultCard from './ResultCard'
import { ask } from '../api'
import type { AskMessage, AskSource, SearchResult } from '../types'

interface Props {
  messages: AskMessage[]
  onMessagesChange: (messages: AskMessage[]) => void
  onOpenPdf: (doc: SearchResult) => void
}

function sourceToResult(s: AskSource): SearchResult {
  return {
    filename: s.filename,
    path: s.path,
    relative_path: s.path,
    snippet: s.snippet,
    tags: {},
  }
}

export default function AskPanel({ messages, onMessagesChange, onOpenPdf }: Props) {
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, loading])

  const lastAssistantIndex = messages.reduceRight(
    (found, msg, i) => (found === -1 && msg.role === 'assistant' ? i : found),
    -1
  )

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    const q = input.trim()
    if (!q || loading) return

    const withUser: AskMessage[] = [...messages, { role: 'user', content: q }]
    onMessagesChange(withUser)
    setInput('')
    setLoading(true)
    setError(null)

    const response = await ask(q, messages)
    setLoading(false)

    if (response.error) {
      setError(response.error)
      return
    }

    onMessagesChange([
      ...withUser,
      {
        role: 'assistant',
        content: response.answer ?? '',
        sources: response.sources ?? [],
      },
    ])
  }

  const handleNewChat = () => {
    onMessagesChange([])
    setError(null)
  }

  return (
    <Box style={{ display: 'flex', flexDirection: 'column', minHeight: 400 }}>
      {/* Chat history */}
      <Box style={{ flex: 1, paddingBottom: '1rem' }}>
        {messages.length === 0 && !loading && (
          <Box style={{ textAlign: 'center', padding: '4rem 2rem', color: 'var(--ink-muted)' }}>
            <Text
              size="xl"
              style={{ fontFamily: '"DM Serif Display", serif', color: 'var(--ink)' }}
            >
              Ask a question about your documents
            </Text>
            <Text size="sm" c="dimmed" mt="xs">
              Try: "What are the key terms in my contracts?" or "Which invoices are over $500?"
            </Text>
          </Box>
        )}

        {messages.map((msg, idx) => (
          <Box key={idx} mb="lg">
            {msg.role === 'user' ? (
              <Box style={{ display: 'flex', justifyContent: 'flex-end' }}>
                <Box
                  style={{
                    background: 'var(--accent)',
                    color: '#fff',
                    borderRadius: '12px 12px 2px 12px',
                    padding: '0.6rem 1rem',
                    maxWidth: '72%',
                  }}
                >
                  <Text size="sm">{msg.content}</Text>
                </Box>
              </Box>
            ) : (
              <Box>
                <Text
                  size="xs"
                  c="dimmed"
                  mb={4}
                  style={{ fontFamily: 'var(--mantine-font-family-monospace)' }}
                >
                  Claude
                </Text>
                <Box
                  style={{
                    background: 'var(--card-bg)',
                    border: '1px solid var(--border)',
                    borderRadius: '2px 12px 12px 12px',
                    padding: '0.75rem 1rem',
                  }}
                >
                  <Text size="sm" style={{ whiteSpace: 'pre-wrap', lineHeight: 1.7 }}>
                    {msg.content}
                  </Text>
                </Box>

                {msg.sources && msg.sources.length > 0 && (
                  <Box mt="sm">
                    {idx === lastAssistantIndex ? (
                      <SimpleGrid cols={{ base: 1, sm: 2, lg: 3 }} spacing="sm" mt="xs">
                        {msg.sources.map((s, si) => (
                          <ResultCard
                            key={si}
                            doc={sourceToResult(s)}
                            query=""
                            selected={false}
                            onToggleSelect={() => {}}
                            onView={onOpenPdf}
                            onDelete={() => {}}
                          />
                        ))}
                      </SimpleGrid>
                    ) : (
                      <Group gap="xs" mt="xs">
                        {msg.sources.map((s, si) => (
                          <Badge
                            key={si}
                            variant="light"
                            color="teal"
                            style={{ cursor: 'pointer' }}
                            onClick={() => onOpenPdf(sourceToResult(s))}
                          >
                            {s.filename}
                          </Badge>
                        ))}
                      </Group>
                    )}
                  </Box>
                )}
              </Box>
            )}
          </Box>
        ))}

        {loading && (
          <Box>
            <Text
              size="xs"
              c="dimmed"
              mb={4}
              style={{ fontFamily: 'var(--mantine-font-family-monospace)' }}
            >
              Claude
            </Text>
            <Box
              style={{
                background: 'var(--card-bg)',
                border: '1px solid var(--border)',
                borderRadius: '2px 12px 12px 12px',
                padding: '0.75rem 1rem',
                display: 'inline-block',
              }}
            >
              <Text size="sm" c="dimmed">● ● ●</Text>
            </Box>
          </Box>
        )}

        {error && (
          <Box
            mt="sm"
            style={{
              background: '#fff5f5',
              border: '1px solid #ffc9c9',
              borderRadius: 6,
              padding: '0.75rem 1rem',
            }}
          >
            <Text size="sm" c="red">{error}</Text>
          </Box>
        )}

        <div ref={bottomRef} />
      </Box>

      {/* Input bar */}
      <Box
        component="form"
        onSubmit={handleSubmit}
        style={{ borderTop: '1px solid var(--border)', paddingTop: '0.75rem' }}
      >
        <Group gap="xs" wrap="nowrap">
          <TextInput
            flex={1}
            placeholder={messages.length > 0 ? 'Ask a follow-up…' : 'Ask a question about your documents…'}
            value={input}
            onChange={(e) => setInput(e.currentTarget.value)}
            size="md"
            disabled={loading}
            styles={{
              input: {
                fontFamily: 'var(--mantine-font-family)',
                background: 'var(--card-bg)',
                borderColor: 'var(--border)',
              },
            }}
          />
          {messages.length > 0 && (
            <Button
              size="md"
              variant="default"
              onClick={handleNewChat}
              title="New chat"
              disabled={loading}
            >
              <IconRefresh size={15} />
            </Button>
          )}
          <Button
            type="submit"
            size="md"
            color="teal"
            loading={loading}
            disabled={!input.trim() || loading}
          >
            <IconSend size={15} />
          </Button>
        </Group>
      </Box>
    </Box>
  )
}
```

- [ ] **Step 2: Verify TypeScript compiles**

```bash
cd "/Users/timothytraviss/Library/CloudStorage/Dropbox/Email Attachments Search/frontend"
npx tsc --noEmit
```
Expected: only App.tsx errors about unused props (fixed in Task 10). No errors in AskPanel.tsx itself.

- [ ] **Step 3: Commit**

```bash
cd ..
git add frontend/src/components/AskPanel.tsx
git commit -m "feat: add AskPanel component — chat history, source cards, follow-up input"
```

---

## Task 10: Wire state and AskPanel — App.tsx

**Files:**
- Modify: `frontend/src/App.tsx`

- [ ] **Step 1: Add imports to App.tsx**

Add to the import block at the top of `App.tsx`:

```typescript
import AskPanel from './components/AskPanel'
import { ask } from './api'
import type { AppMode, AskMessage } from './types'
```

(Remove `ask` from the api import if it was already listed; add it if not.)

- [ ] **Step 2: Add searchMode and askMessages state**

After the existing `const [showWelcome, setShowWelcome] = useState(true)` line (around line 55), add:

```typescript
  const [searchMode, setSearchMode] = useState<AppMode>('search')
  const [askMessages, setAskMessages] = useState<AskMessage[]>([])
```

- [ ] **Step 3: Pass appMode and onModeChange to SearchBar**

Find the `<SearchBar` block in the JSX (around line 194). Add the two new props:

```typescript
              <SearchBar
                filters={filters}
                tagYears={tagYears}
                companies={companies}
                resultCount={searchMode === 'search' ? total : null}
                isIndexing={isIndexing}
                appMode={searchMode}
                onModeChange={setSearchMode}
                onSearch={handleSearch}
                onClear={handleClear}
                onExportCsv={() => exportCsv(filters)}
                onOpenReindex={() => setReindexOpen(true)}
                onOpenFilePdfs={() => setFilePdfsOpen(true)}
                onOpenTagMgmt={() => setTagMgmtOpen(true)}
                onOpenStats={() => setStatsOpen(true)}
              />
```

- [ ] **Step 4: Render AskPanel in place of results when in Ask mode**

Find the `{/* Welcome state */}` comment (around line 210 in App.tsx). The entire block from `{/* Welcome state */}` through the closing `</AnimatePresence>` of the results grid (around line 295) needs to be wrapped in the `else` branch of a ternary, with the AskPanel as the `if` branch.

In App.tsx, replace this section (from the welcome AnimatePresence open tag to the results grid AnimatePresence close tag) with:

```typescript
            {searchMode === 'ask' ? (
              <AskPanel
                messages={askMessages}
                onMessagesChange={setAskMessages}
                onOpenPdf={handleView}
              />
            ) : (
              <>
                {/* Welcome state */}
                <AnimatePresence>
                  {showWelcome && (
                    <motion.div
                      key="welcome"
                      initial={{ opacity: 0 }}
                      animate={{ opacity: 1 }}
                      exit={{ opacity: 0 }}
                      transition={{ duration: 0.25 }}
                    >
                      <WelcomeState
                        stats={stats}
                        companies={companies}
                        onSearch={handleQuickSearch}
                      />
                    </motion.div>
                  )}
                </AnimatePresence>

                {/* Loading */}
                {isSearching && results.length === 0 && (
                  <Center py="xl">
                    <Text c="dimmed" size="sm">Searching…</Text>
                  </Center>
                )}

                {/* No results */}
                {!isSearching && !showWelcome && results.length === 0 && (
                  <Center py="xl">
                    <Text c="dimmed">No results found. Try different keywords or filters.</Text>
                  </Center>
                )}

                {/* Results grid */}
                <AnimatePresence>
                  {results.length > 0 && (
                    <motion.div
                      key="results"
                      initial={{ opacity: 0 }}
                      animate={{ opacity: 1 }}
                      transition={{ duration: 0.2 }}
                    >
                      <SimpleGrid cols={{ base: 1, sm: 2, lg: 3 }} spacing="md">
                        {results.map((doc, i) => (
                          <motion.div
                            key={doc.path}
                            initial={{ opacity: 0, y: 12 }}
                            animate={{ opacity: 1, y: 0 }}
                            transition={{ duration: 0.2, delay: Math.min(i * 0.03, 0.3) }}
                          >
                            <ResultCard
                              doc={doc}
                              query={filters.q}
                              selected={selectedPaths.has(doc.path)}
                              onToggleSelect={toggleSelect}
                              onView={handleView}
                              onDelete={setDeleteTarget}
                            />
                          </motion.div>
                        ))}
                      </SimpleGrid>

                      {hasMore && (
                        <Center mt="lg">
                          <Button
                            variant="default"
                            loading={isSearching}
                            onClick={() => runSearch(activeFiltersRef.current, true)}
                          >
                            Load more
                          </Button>
                        </Center>
                      )}

                      <BulkToolbar
                        selectedPaths={selectedPaths}
                        companies={companies}
                        onApplied={() => {
                          setSelectedPaths(new Set())
                          runSearch(activeFiltersRef.current, false)
                        }}
                        onDeselect={() => setSelectedPaths(new Set())}
                      />
                    </motion.div>
                  )}
                </AnimatePresence>
              </>
            )}
```

- [ ] **Step 5: Verify TypeScript compiles with no errors**

```bash
cd "/Users/timothytraviss/Library/CloudStorage/Dropbox/Email Attachments Search/frontend"
npx tsc --noEmit
```
Expected: no errors.

- [ ] **Step 6: Start dev server and test manually**

```bash
# Terminal 1 — backend
cd "/Users/timothytraviss/Library/CloudStorage/Dropbox/Email Attachments Search"
source venv/bin/activate
python backend/app.py

# Terminal 2 — frontend
cd "/Users/timothytraviss/Library/CloudStorage/Dropbox/Email Attachments Search/frontend"
npm run dev
```

Open `http://localhost:5173`. Verify:
- Toggle shows "Search documents" / "Ask AI"
- Switching to Ask mode shows the empty AskPanel state
- Switching back to Search mode shows the search bar and results
- Asking a question (with embeddings built) returns an answer with source cards

- [ ] **Step 7: Commit**

```bash
cd ..
git add frontend/src/App.tsx
git commit -m "feat: wire AskPanel into App — searchMode state, AskPanel render branch"
```

---

## Task 11: Add Rebuild Embeddings button — ReindexModal.tsx

**Files:**
- Modify: `frontend/src/components/ReindexModal.tsx`

- [ ] **Step 1: Add new imports to ReindexModal.tsx**

Add to the existing import from `'../api'`:

```typescript
import { startReindex, getReindexStatus, startRebuildEmbeddings, getRebuildEmbeddingsStatus } from '../api'
```

- [ ] **Step 2: Add rebuild state variables**

After the existing `const pollingRef = useRef(false)` line, add:

```typescript
  const [rebuildRunning, setRebuildRunning] = useState(false)
  const [rebuildLogs, setRebuildLogs] = useState<string[]>([])
  const [rebuildDone, setRebuildDone] = useState(false)
  const rebuildPollingRef = useRef(false)
```

- [ ] **Step 3: Add the poll function for rebuild**

After the existing `poll()` function, add:

```typescript
  async function pollRebuild() {
    if (rebuildPollingRef.current) return
    rebuildPollingRef.current = true
    let lastLen = 0
    while (true) {
      await new Promise((r) => setTimeout(r, 1000))
      try {
        const s = await getRebuildEmbeddingsStatus()
        if (s.logs && s.logs.length > lastLen) {
          setRebuildLogs(s.logs)
          lastLen = s.logs.length
        }
        if (!s.running) {
          rebuildPollingRef.current = false
          setRebuildRunning(false)
          setRebuildDone(true)
          if (s.error) {
            setRebuildLogs((prev) => [...prev, `Error: ${s.error}`])
          }
          break
        }
      } catch {
        rebuildPollingRef.current = false
        setRebuildRunning(false)
        break
      }
    }
  }
```

- [ ] **Step 4: Add the handler for starting a rebuild**

After the existing `handleStart` function, add:

```typescript
  const handleRebuildEmbeddings = async () => {
    setRebuildLogs([])
    setRebuildDone(false)
    setRebuildRunning(true)
    try {
      await startRebuildEmbeddings()
      pollRebuild()
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : 'Unknown error'
      notifications.show({ color: 'red', message: `Failed to rebuild embeddings: ${msg}` })
      setRebuildRunning(false)
    }
  }
```

- [ ] **Step 5: Add the Rebuild Embeddings UI section**

Add a `<Divider />` and the new section inside the `<Stack gap="md">`, after the existing log scroll area block:

```typescript
        <Divider my="xs" label="Semantic Search" labelPosition="left" />

        <Text size="sm" c="dimmed">
          Rebuild the AI embeddings index used by{' '}
          <strong>Ask AI</strong> mode. Run this after a full re-index when new
          documents have been added.
        </Text>

        <Group>
          <Button
            variant="light"
            color="teal"
            loading={rebuildRunning}
            disabled={rebuildRunning}
            onClick={handleRebuildEmbeddings}
          >
            {rebuildRunning ? 'Building embeddings…' : 'Rebuild embeddings'}
          </Button>
          {rebuildDone && (
            <Text size="sm" c="teal">✓ Done</Text>
          )}
        </Group>

        {rebuildLogs.length > 0 && (
          <ScrollArea
            h={160}
            style={{ background: '#0f1724', borderRadius: 6, padding: '0.75rem' }}
          >
            <Box
              component="pre"
              style={{
                fontFamily: 'var(--mantine-font-family-monospace)',
                fontSize: 12,
                color: '#e6eef8',
                margin: 0,
                whiteSpace: 'pre-wrap',
                wordBreak: 'break-all',
              }}
            >
              {rebuildLogs.join('\n')}
            </Box>
          </ScrollArea>
        )}
```

- [ ] **Step 6: Verify TypeScript compiles**

```bash
cd "/Users/timothytraviss/Library/CloudStorage/Dropbox/Email Attachments Search/frontend"
npx tsc --noEmit
```
Expected: no errors.

- [ ] **Step 7: Build frontend and run sync**

```bash
cd "/Users/timothytraviss/Library/CloudStorage/Dropbox/Email Attachments Search"
bash sync_bundle.sh
```
Expected: frontend builds without errors, bundle is synced.

- [ ] **Step 8: Final smoke test**

Open `http://localhost:5173` (or the .app bundle). Verify:
1. Tools → Re-index — scroll down — "Rebuild embeddings" button is visible
2. Click Rebuild embeddings — progress log streams — "Done. N chunks embedded." appears
3. Switch to Ask AI mode — type a question — answer appears with source cards
4. Ask a follow-up — answer updates, previous source cards collapse to badges
5. Click a badge — PdfModal opens the correct PDF
6. "New chat" button clears history
7. Switch back to Search documents — existing search works unchanged

- [ ] **Step 9: Commit**

```bash
git add frontend/src/components/ReindexModal.tsx
git commit -m "feat: add Rebuild Embeddings section to ReindexModal"
```

---

## Post-Implementation: Bundle the anthropic package

After all tasks pass, do a full py2app rebuild once to include `anthropic` in the `.app` bundle:

```bash
cd "/Users/timothytraviss/Library/CloudStorage/Dropbox/Email Attachments Search"
source venv/bin/activate
python setup.py py2app
```

This is required for the `.app` bundle to work — `sync_bundle.sh` alone does not install new Python packages.
