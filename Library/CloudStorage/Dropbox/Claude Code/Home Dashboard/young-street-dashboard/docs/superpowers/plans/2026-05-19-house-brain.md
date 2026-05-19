# House Brain Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a Flask backend with FAISS vector search and a terminal-style AI chat drawer to the 11 Young Street dashboard, replacing `python3 -m http.server 8080`.

**Architecture:** Flask serves `../` (project root) as static files AND `/api/*` routes on port 8080. FAISS IndexFlatL2 + OpenAI `text-embedding-3-small` for document retrieval. Anthropic `claude-sonnet-4-6` for answers grounded in property documents. SQLite for document metadata and mtime-based incremental indexing.

**Tech Stack:** Python 3 (Flask, pdfminer.six, faiss-cpu, openai, anthropic, python-dotenv), SQLite + FTS5, vanilla JS ES modules (no build step)

**Full spec:** `docs/superpowers/specs/2026-05-19-house-brain-design.md`

**Run tests:** `cd backend && python -m pytest tests/ -v`

---

### Task 1: Backend scaffold + Flask server

**Files:**
- Create: `backend/requirements.txt`
- Create: `backend/app.py`
- Create: `backend/.env` (gitignored, API keys)
- Modify: `.gitignore`

- [ ] **Step 1: Update .gitignore**

Add to `.gitignore` (at project root):
```
# Backend
backend/.env
backend/house.db
backend/house.faiss
backend/house_metadata.json
backend/__pycache__/
backend/tests/__pycache__/
.superpowers/
```

- [ ] **Step 2: Create `backend/requirements.txt`**

```
flask>=3.0
python-dotenv>=1.0
pdfminer.six>=20221105
faiss-cpu>=1.8
openai>=1.0
anthropic>=0.40
numpy>=1.26
pytest>=8.0
```

- [ ] **Step 3: Install dependencies**

Run: `cd backend && pip install -r requirements.txt`

Expected: All packages install without error.

- [ ] **Step 4: Create `backend/app.py`** (minimal — just static serving + health route)

```python
import os
import sys
from flask import Flask, send_from_directory, jsonify
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), '.env'))

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
app = Flask(__name__)


@app.route('/')
def index():
    return send_from_directory(ROOT, 'index.html')


@app.route('/api/health')
def health():
    return jsonify({'status': 'ok'})


@app.route('/<path:path>')
def serve_static(path):
    return send_from_directory(ROOT, path)


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port, debug=True)
```

- [ ] **Step 5: Create `backend/.env`**

```
ANTHROPIC_API_KEY=sk-ant-...
OPENAI_API_KEY=sk-...
DOCUMENTS_FOLDER=/Users/timothytraviss/Library/CloudStorage/Dropbox/11 Young Street/
PORT=8080
```

Replace key values. Do not commit this file.

- [ ] **Step 6: Start server and verify**

Run: `cd backend && python app.py`

In another terminal:
```
curl http://localhost:8080/api/health
# Expected: {"status":"ok"}

curl -s http://localhost:8080/ | head -5
# Expected: first lines of index.html
```

Dashboard should be fully functional at `http://localhost:8080`.

- [ ] **Step 7: Commit**

```bash
git checkout -b feature/house-brain
git add backend/requirements.txt backend/app.py .gitignore
git commit -m "feat: Flask backend scaffold serving static + /api/health"
```

---

### Task 2: Database layer

**Files:**
- Create: `backend/database.py`
- Create: `backend/tests/__init__.py` (empty)
- Create: `backend/tests/conftest.py`
- Create: `backend/tests/test_database.py`

- [ ] **Step 1: Write failing tests**

Create `backend/tests/__init__.py` (empty file).

Create `backend/tests/conftest.py`:
```python
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
```

Create `backend/tests/test_database.py`:
```python
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && python -m pytest tests/test_database.py -v`

Expected: `ImportError: No module named 'database'` (file does not exist yet).

- [ ] **Step 3: Create `backend/database.py`**

```python
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
    conn.close()


def upsert_document(path, filename, name, mtime, text):
    snippet = (text or '')[:200]
    indexed_at = datetime.now(timezone.utc).isoformat()
    conn = get_connection()
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
    conn.close()


def get_document_count():
    conn = get_connection()
    count = conn.execute('SELECT COUNT(*) FROM documents').fetchone()[0]
    conn.close()
    return count


def get_last_indexed():
    conn = get_connection()
    row = conn.execute('SELECT MAX(indexed_at) FROM documents').fetchone()
    conn.close()
    return row[0] if row else None


def get_all_documents():
    conn = get_connection()
    rows = conn.execute(
        'SELECT path, filename, name, mtime FROM documents'
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_all_documents_with_text():
    conn = get_connection()
    rows = conn.execute(
        'SELECT path, filename, name, text FROM documents'
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]
```

- [ ] **Step 4: Run tests and verify they pass**

Run: `cd backend && python -m pytest tests/test_database.py -v`

Expected: `5 passed`

- [ ] **Step 5: Commit**

```bash
git add backend/database.py backend/tests/
git commit -m "feat: SQLite database layer with FTS5 and document CRUD"
```

---

### Task 3: Indexer

**Files:**
- Create: `backend/indexer.py`
- Create: `backend/tests/test_indexer.py`

- [ ] **Step 1: Write failing tests**

Create `backend/tests/test_indexer.py`:
```python
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && python -m pytest tests/test_indexer.py -v`

Expected: `ImportError: No module named 'indexer'`

- [ ] **Step 3: Create `backend/indexer.py`**

```python
import os
import json
from pdfminer.high_level import extract_text
from database import get_all_documents, upsert_document

PROPERTY_JSON = os.path.abspath(
    os.path.join(os.path.dirname(__file__), '..', 'property.json')
)


def load_doc_names():
    """Return {lowercase_name: display_name} from property.json documents array."""
    try:
        with open(PROPERTY_JSON) as f:
            data = json.load(f)
        return {d['name'].lower(): d['name'] for d in data.get('documents', [])}
    except Exception:
        return {}


def scan_pdfs(folder, progress_callback=None):
    """
    Walk folder for PDFs, skip files with matching mtime, extract and index new ones.
    Returns (indexed_count, skipped_count).
    """
    existing = {d['path']: d['mtime'] for d in get_all_documents()}
    doc_names = load_doc_names()

    pdf_paths = []
    for root, _, files in os.walk(folder):
        for fname in sorted(files):
            if fname.lower().endswith('.pdf'):
                pdf_paths.append(os.path.join(root, fname))

    indexed = 0
    skipped = 0
    total = len(pdf_paths)

    for i, path in enumerate(pdf_paths):
        mtime = os.path.getmtime(path)
        filename = os.path.basename(path)
        stem = os.path.splitext(filename)[0]
        name = doc_names.get(stem.lower(), stem)

        if progress_callback:
            progress_callback(f'{i + 1}/{total} {filename}')

        if path in existing and existing[path] == mtime:
            skipped += 1
            continue

        try:
            text = extract_text(path) or ''
        except Exception as exc:
            if progress_callback:
                progress_callback(f'ERROR {filename}: {exc}')
            continue

        upsert_document(
            path=path, filename=filename, name=name,
            mtime=mtime, text=text,
        )
        indexed += 1

    return indexed, skipped
```

- [ ] **Step 4: Run tests and verify they pass**

Run: `cd backend && python -m pytest tests/test_indexer.py -v`

Expected: `3 passed`

- [ ] **Step 5: Commit**

```bash
git add backend/indexer.py backend/tests/test_indexer.py
git commit -m "feat: PDF indexer with mtime-based incremental skip"
```

---

### Task 4: Embeddings + FAISS

**Files:**
- Create: `backend/embeddings.py`
- Create: `backend/tests/test_embeddings.py`

- [ ] **Step 1: Write failing tests**

Create `backend/tests/test_embeddings.py`:
```python
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && python -m pytest tests/test_embeddings.py -v`

Expected: `ImportError: No module named 'embeddings'`

- [ ] **Step 3: Create `backend/embeddings.py`**

```python
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
        chunks.append(text[start:start + size])
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
```

- [ ] **Step 4: Run tests and verify they pass**

Run: `cd backend && python -m pytest tests/test_embeddings.py -v`

Expected: `5 passed`

- [ ] **Step 5: Commit**

```bash
git add backend/embeddings.py backend/tests/test_embeddings.py
git commit -m "feat: FAISS embeddings with chunking and vector search"
```

---

### Task 5: /api/ask endpoint

**Files:**
- Modify: `backend/app.py`

- [ ] **Step 1: Add imports and Anthropic client to `backend/app.py`**

Add after the existing imports:
```python
import json
import threading
from anthropic import Anthropic

_anthropic = None

def _ant():
    global _anthropic
    if _anthropic is None:
        _anthropic = Anthropic()
    return _anthropic

PROPERTY_JSON = os.path.abspath(
    os.path.join(os.path.dirname(__file__), '..', 'property.json')
)
```

- [ ] **Step 2: Add `/api/ask` route to `backend/app.py`**

Add after the `/api/health` route:
```python
@app.route('/api/ask', methods=['POST'])
def api_ask():
    from flask import request
    body = request.get_json(force=True) or {}
    query = (body.get('query') or '').strip()
    messages = body.get('messages') or []

    if not query:
        return jsonify({'error': 'query required'}), 400

    # Load property facts as system context
    try:
        with open(PROPERTY_JSON) as f:
            property_ctx = json.dumps(json.load(f), indent=2)
    except Exception:
        property_ctx = '{}'

    # Vector search (graceful fallback if index not built)
    try:
        from embeddings import search_chunks
        chunks = search_chunks(query, top_k=6)
    except Exception:
        chunks = []

    doc_ctx = ''.join(
        f'\n\n---\nDocument: {c["name"]} ({c["filename"]})\n{c["snippet"]}'
        for c in chunks
    )

    system_prompt = (
        'You are the House Brain for 11 Young Street, Scotts Landing, '
        'Mahurangi East, New Zealand.\n'
        'Answer questions about the property using the facts and document excerpts provided. '
        'Be concise. Cite the document name when you draw from it.\n\n'
        f'PROPERTY FACTS:\n{property_ctx}\n\n'
        f'RELEVANT DOCUMENT EXCERPTS:{doc_ctx or " (none — index not yet built)"}'
    )

    history = [m for m in messages if m.get('role') in ('user', 'assistant')]
    history.append({'role': 'user', 'content': query})

    resp = _ant().messages.create(
        model='claude-sonnet-4-6',
        max_tokens=1024,
        system=system_prompt,
        messages=history,
    )
    answer = resp.content[0].text

    seen = set()
    sources = []
    for c in chunks:
        if c['filename'] not in seen:
            seen.add(c['filename'])
            sources.append({
                'filename': c['filename'],
                'name':     c['name'],
                'snippet':  c['snippet'],
            })

    return jsonify({'answer': answer, 'sources': sources})
```

- [ ] **Step 3: Verify with curl**

Start server: `cd backend && python app.py`

```bash
curl -s -X POST http://localhost:8080/api/ask \
  -H 'Content-Type: application/json' \
  -d '{"query":"What is the address of the property?","messages":[]}' | python3 -m json.tool
```

Expected: JSON response with `"answer"` containing the address and `"sources"` array (possibly empty if not yet indexed).

- [ ] **Step 4: Commit**

```bash
git add backend/app.py
git commit -m "feat: /api/ask — FAISS search + Claude answer with source citations"
```

---

### Task 6: /api/index + /api/index/status endpoints

**Files:**
- Modify: `backend/app.py`

- [ ] **Step 1: Add index state and background runner to `backend/app.py`**

Add after the `_ant()` function (before route definitions):
```python
_index_state = {
    'running':      False,
    'progress':     '',
    'log':          [],
    'error':        None,
}


def _run_index(folder):
    _index_state['running'] = True
    _index_state['log'] = []
    _index_state['error'] = None

    def log(msg):
        _index_state['log'].append(msg)
        _index_state['progress'] = msg

    try:
        from database import init_db, get_all_documents_with_text
        from indexer import scan_pdfs
        from embeddings import build_embeddings

        init_db()
        log('Scanning PDFs...')
        indexed, skipped = scan_pdfs(folder, progress_callback=log)
        log(f'Indexed {indexed} new, skipped {skipped} unchanged')

        log('Building embeddings...')
        docs = get_all_documents_with_text()
        build_embeddings(docs, progress_callback=log)
        log('Complete')
    except Exception as exc:
        _index_state['error'] = str(exc)
        log(f'ERROR: {exc}')
    finally:
        _index_state['running'] = False
```

- [ ] **Step 2: Add `/api/index` and `/api/index/status` routes to `backend/app.py`**

Add after the `/api/ask` route:
```python
@app.route('/api/index', methods=['POST'])
def api_index():
    if _index_state['running']:
        return jsonify({'status': 'already_running'}), 409

    folder = os.environ.get('DOCUMENTS_FOLDER', '').strip()
    if not folder or not os.path.isdir(folder):
        return jsonify({'error': 'DOCUMENTS_FOLDER not set or not a valid directory'}), 500

    thread = threading.Thread(target=_run_index, args=(folder,), daemon=True)
    thread.start()
    return jsonify({'status': 'started'})


@app.route('/api/index/status')
def api_index_status():
    from database import get_document_count, get_last_indexed
    try:
        doc_count    = get_document_count()
        last_indexed = get_last_indexed()
    except Exception:
        doc_count    = 0
        last_indexed = None

    return jsonify({
        'running':      _index_state['running'],
        'progress':     _index_state['progress'],
        'log':          list(_index_state['log'][-5:]),
        'error':        _index_state['error'],
        'doc_count':    doc_count,
        'last_indexed': last_indexed,
    })
```

- [ ] **Step 3: Verify with curl**

Start server: `cd backend && python app.py`

```bash
# Start indexing
curl -s -X POST http://localhost:8080/api/index | python3 -m json.tool
# Expected: {"status":"started"}

# Poll status
curl -s http://localhost:8080/api/index/status | python3 -m json.tool
# Expected: {"running":true/false, "progress":"...", "log":[...], ...}
```

- [ ] **Step 4: Commit**

```bash
git add backend/app.py
git commit -m "feat: /api/index and /api/index/status for background document indexing"
```

---

### Task 7: Chat drawer HTML + CSS

**Files:**
- Modify: `index.html`
- Modify: `style.css`

- [ ] **Step 1: Add `#btn-chat` to `.controls` in `index.html`**

In `index.html`, add `#btn-chat` between `#btn-focus` and `#btn-admin`:
```html
    <button id="btn-chat" class="ctrl-btn" aria-label="Open House Brain">
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
        <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>
        <line x1="9" y1="10" x2="15" y2="10"/>
        <line x1="9" y1="14" x2="13" y2="14"/>
      </svg>
    </button>
```

- [ ] **Step 2: Add chat drawer and scrim to `index.html`**

Add after `</aside>` (closing admin panel) and before `<!-- Floor plan page navigation -->`:
```html
  <!-- Chat scrim -->
  <div class="chat-scrim" id="chat-scrim"></div>

  <!-- Chat drawer (slide-in from left) -->
  <aside class="chat-drawer" id="chat-drawer">
    <header class="chat-head">
      <div class="chat-head-left">
        <div class="chat-eyebrow">house-brain</div>
        <div class="chat-title">~/11-young-st</div>
      </div>
      <button class="chat-close" id="chat-close" aria-label="Close">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round">
          <path d="M18 6 6 18M6 6l12 12"/>
        </svg>
      </button>
    </header>

    <div class="chat-messages" id="chat-messages">
      <div class="chat-welcome">
        <span class="chat-prompt">❯</span>
        <span class="chat-welcome-text">Ask anything about the property…</span>
      </div>
    </div>

    <div class="chat-input-row">
      <span class="chat-prompt">❯</span>
      <input type="text" id="chat-input" class="chat-input" placeholder="ask about the house" autocomplete="off" spellcheck="false">
      <button id="chat-send" class="chat-send" aria-label="Send">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <line x1="12" y1="19" x2="12" y2="5"/>
          <polyline points="5 12 12 5 19 12"/>
        </svg>
      </button>
    </div>
  </aside>
```

- [ ] **Step 3: Add chat drawer styles to `style.css`**

Append to `style.css`:
```css
/* ─── Chat drawer ─────────────────────────────────── */

.chat-scrim {
  display: none;
  position: fixed;
  inset: 0;
  background: rgba(0,0,0,0.45);
  z-index: 190;
  backdrop-filter: blur(2px);
}
.chat-scrim.open { display: block; }

.chat-drawer {
  position: fixed;
  top: 0;
  left: 0;
  height: 100%;
  width: 360px;
  max-width: 90vw;
  transform: translateX(-100%);
  transition: transform 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  z-index: 200;
  display: flex;
  flex-direction: column;
  background: rgba(4, 8, 12, 0.97);
  border-right: 1px solid rgba(var(--accent-rgb, 52,211,153), 0.2);
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
  font-family: 'Electrolize', monospace;
}
.chat-drawer.open { transform: translateX(0); }

.chat-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 16px 12px;
  border-bottom: 1px solid rgba(var(--accent-rgb, 52,211,153), 0.15);
  flex-shrink: 0;
}
.chat-eyebrow {
  font-size: 10px;
  text-transform: uppercase;
  letter-spacing: .1em;
  color: var(--accent, #34d399);
  opacity: .8;
  margin-bottom: 2px;
}
.chat-title {
  font-size: 11px;
  color: rgba(255,255,255,0.3);
}
.chat-close {
  width: 26px;
  height: 26px;
  border: 1px solid rgba(var(--accent-rgb, 52,211,153), 0.2);
  border-radius: 6px;
  background: none;
  color: rgba(255,255,255,0.4);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: background .15s, color .15s;
}
.chat-close:hover {
  background: rgba(var(--accent-rgb, 52,211,153), 0.1);
  color: rgba(255,255,255,0.8);
}

.chat-messages {
  flex: 1;
  overflow-y: auto;
  padding: 14px 16px 8px;
  display: flex;
  flex-direction: column;
  gap: 14px;
  scrollbar-width: thin;
  scrollbar-color: rgba(255,255,255,0.1) transparent;
}

.chat-welcome {
  display: flex;
  align-items: center;
  gap: 8px;
  opacity: .4;
}
.chat-welcome-text { font-size: 12px; color: rgba(255,255,255,0.6); }

/* Message blocks */
.chat-msg { display: flex; flex-direction: column; gap: 4px; }

.chat-msg-user {
  font-size: 11px;
  color: var(--accent, #34d399);
  opacity: .85;
  display: flex;
  gap: 6px;
  align-items: flex-start;
}
.chat-prompt {
  font-size: 12px;
  color: var(--accent, #34d399);
  opacity: .7;
  flex-shrink: 0;
  line-height: 1.6;
}

.chat-msg-ai {
  font-size: 11.5px;
  color: rgba(230, 244, 238, 0.82);
  line-height: 1.7;
  padding-left: 18px;
  white-space: pre-wrap;
  word-break: break-word;
}
.chat-msg-ai .chat-bullet {
  color: var(--accent, #34d399);
  opacity: .7;
}

.chat-msg-source {
  font-size: 9.5px;
  color: rgba(255,255,255,0.3);
  padding-left: 18px;
  margin-top: 2px;
  letter-spacing: .02em;
}

.chat-msg-thinking {
  font-size: 11px;
  color: rgba(255,255,255,0.3);
  padding-left: 18px;
  display: flex;
  align-items: center;
  gap: 6px;
}
.chat-dots {
  display: flex;
  gap: 3px;
  align-items: center;
}
.chat-dots span {
  width: 4px;
  height: 4px;
  background: var(--accent, #34d399);
  border-radius: 50%;
  animation: chat-pulse 1.2s ease-in-out infinite;
}
.chat-dots span:nth-child(2) { animation-delay: .2s; }
.chat-dots span:nth-child(3) { animation-delay: .4s; }
@keyframes chat-pulse {
  0%, 80%, 100% { opacity: .15; }
  40% { opacity: .8; }
}

/* Input bar */
.chat-input-row {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 14px 12px;
  border-top: 1px solid rgba(var(--accent-rgb, 52,211,153), 0.12);
  flex-shrink: 0;
}
.chat-input {
  flex: 1;
  background: none;
  border: none;
  outline: none;
  font-family: 'Electrolize', monospace;
  font-size: 12px;
  color: rgba(255,255,255,0.75);
  caret-color: var(--accent, #34d399);
}
.chat-input::placeholder { color: rgba(255,255,255,0.2); }
.chat-send {
  width: 26px;
  height: 26px;
  border: 1px solid rgba(var(--accent-rgb, 52,211,153), 0.3);
  border-radius: 6px;
  background: rgba(var(--accent-rgb, 52,211,153), 0.12);
  color: var(--accent, #34d399);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: background .15s;
  flex-shrink: 0;
}
.chat-send:hover { background: rgba(var(--accent-rgb, 52,211,153), 0.25); }
```

- [ ] **Step 4: Verify drawer renders**

Open `http://localhost:8080` in a browser. The chat button (speech bubble icon) should appear in the controls bar. Clicking it does nothing yet — the JS is in Task 8.

Verify no console errors on page load.

- [ ] **Step 5: Commit**

```bash
git add index.html style.css
git commit -m "feat: chat drawer HTML + terminal-style CSS"
```

---

### Task 8: chat.js panel

**Files:**
- Create: `js/panels/chat.js`
- Modify: `app.js`

- [ ] **Step 1: Create `js/panels/chat.js`**

```javascript
export function initChat() {
  const drawer   = document.getElementById('chat-drawer');
  const scrim    = document.getElementById('chat-scrim');
  const openBtn  = document.getElementById('btn-chat');
  const closeBtn = document.getElementById('chat-close');
  const messages = document.getElementById('chat-messages');
  const input    = document.getElementById('chat-input');
  const sendBtn  = document.getElementById('chat-send');

  // In-memory conversation history (session only)
  const history = [];

  function open() {
    drawer.classList.add('open');
    scrim.classList.add('open');
    openBtn.classList.add('active');
    input.focus();
  }

  function close() {
    drawer.classList.remove('open');
    scrim.classList.remove('open');
    openBtn.classList.remove('active');
  }

  openBtn.addEventListener('click', () =>
    drawer.classList.contains('open') ? close() : open()
  );
  closeBtn.addEventListener('click', close);
  scrim.addEventListener('click', close);
  document.addEventListener('keydown', e => {
    if (e.key === 'Escape') close();
  });

  sendBtn.addEventListener('click', submit);
  input.addEventListener('keydown', e => {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); submit(); }
  });

  async function submit() {
    const text = input.value.trim();
    if (!text) return;
    input.value = '';

    appendUser(text);
    const thinking = appendThinking();
    scrollBottom();

    try {
      const res = await fetch('/api/ask', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query: text, messages: history }),
      });
      const data = await res.json();
      thinking.remove();

      if (data.error) {
        appendError(data.error);
      } else {
        appendAI(data.answer, data.sources || []);
        history.push({ role: 'user',      content: text });
        history.push({ role: 'assistant', content: data.answer });
      }
    } catch (err) {
      thinking.remove();
      appendError('Connection error — is the Flask server running?');
    }

    scrollBottom();
  }

  function appendUser(text) {
    const div = document.createElement('div');
    div.className = 'chat-msg';
    div.innerHTML = `
      <div class="chat-msg-user">
        <span class="chat-prompt">❯</span>
        <span>${escHtml(text)}</span>
      </div>`;
    messages.appendChild(div);
  }

  function appendThinking() {
    const div = document.createElement('div');
    div.className = 'chat-msg chat-msg-thinking';
    div.innerHTML = `
      <div class="chat-dots">
        <span></span><span></span><span></span>
      </div>
      searching documents…`;
    messages.appendChild(div);
    return div;
  }

  function appendAI(text, sources) {
    const div = document.createElement('div');
    div.className = 'chat-msg';

    // Render answer: replace leading "- " or "• " list items with → bullets
    const rendered = text
      .split('\n')
      .map(line => {
        if (/^\s*[-•]\s/.test(line)) {
          return `<span class="chat-bullet">→</span> ${escHtml(line.replace(/^\s*[-•]\s*/, ''))}`;
        }
        return escHtml(line);
      })
      .join('\n');

    let html = `<div class="chat-msg-ai">${rendered}</div>`;

    if (sources.length > 0) {
      const srcLine = sources
        .map(s => escHtml(s.name || s.filename))
        .join(' · ');
      html += `<div class="chat-msg-source">─ ${srcLine}</div>`;
    }

    div.innerHTML = html;
    messages.appendChild(div);
  }

  function appendError(msg) {
    const div = document.createElement('div');
    div.className = 'chat-msg';
    div.innerHTML = `<div class="chat-msg-ai" style="opacity:.5">${escHtml(msg)}</div>`;
    messages.appendChild(div);
  }

  function scrollBottom() {
    messages.scrollTop = messages.scrollHeight;
  }

  function escHtml(str) {
    return String(str)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }
}
```

- [ ] **Step 2: Import and call `initChat` in `app.js`**

Add `import { initChat } from './js/panels/chat.js';` to the imports block and `initChat();` after `initFloorPlan(map);`.

The imports section should become:
```javascript
import { initMap }       from './js/map.js';
import { initTheme }     from './js/theme.js';
import { initAdmin }     from './js/admin.js';
import { initClock }     from './js/panels/clock.js';
import { initWeather }   from './js/panels/weather.js';
import { initProperty }  from './js/panels/property.js';
import { initTides }     from './js/panels/tides.js';
import { initFloorPlan } from './js/floorplan.js';
import { initFocus }     from './js/focus.js';
import { initChat }      from './js/panels/chat.js';
import { applyState }    from './js/state.js';
```

And the call order:
```javascript
applyState();
const { map } = initMap();
initTheme(map);
initAdmin();
initFocus();
initChat();
const clock = initClock();
initWeather(clock);
initProperty();
initTides();
initFloorPlan(map);
```

- [ ] **Step 3: Verify in browser**

1. Open `http://localhost:8080`
2. Click the chat icon (speech bubble) in controls → drawer slides in from left
3. Type "What is the address of this property?" → "searching documents…" appears → answer arrives
4. Source citation appears below answer (or absent if FAISS not yet indexed)
5. Press Escape → drawer closes
6. Open focus mode (H) → panels hide → chat button still visible, drawer still opens

- [ ] **Step 4: Commit**

```bash
git add js/panels/chat.js app.js
git commit -m "feat: terminal-style chat drawer with conversation history"
```

---

### Task 9: Admin panel — House Brain section

**Files:**
- Modify: `index.html`
- Modify: `js/admin.js`

- [ ] **Step 1: Add House Brain HTML to `index.html`**

In `index.html`, inside `.admin-body`, add before the `<!-- Reset -->` section:
```html
      <!-- House Brain -->
      <div class="admin-section">
        <div class="admin-section-label">House Brain</div>
        <button class="hb-btn" id="hb-index-btn">
          <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="margin-right:8px;flex-shrink:0">
            <polyline points="1 4 1 10 7 10"/><path d="M3.51 15a9 9 0 1 0 2.13-9.36L1 10"/>
          </svg>
          Index Documents
        </button>
        <div class="hb-log" id="hb-log"></div>
        <div class="hb-status" id="hb-status"></div>
      </div>
```

- [ ] **Step 2: Add House Brain styles to `style.css`**

Append to `style.css`:
```css
/* ─── Admin: House Brain section ──────────────────── */

.hb-btn {
  width: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 8px 14px;
  background: rgba(var(--accent-rgb, 52,211,153), 0.12);
  border: 1px solid rgba(var(--accent-rgb, 52,211,153), 0.3);
  border-radius: 8px;
  color: var(--accent, #34d399);
  font-size: 12px;
  cursor: pointer;
  transition: background .15s;
}
.hb-btn:hover:not(:disabled) { background: rgba(var(--accent-rgb, 52,211,153), 0.22); }
.hb-btn:disabled { opacity: .5; cursor: not-allowed; }

.hb-log {
  margin-top: 8px;
  font-family: 'Electrolize', monospace;
  font-size: 10px;
  color: rgba(255,255,255,0.35);
  line-height: 1.6;
  min-height: 0;
  max-height: 64px;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  gap: 1px;
}

.hb-status {
  margin-top: 6px;
  font-size: 10px;
  color: rgba(255,255,255,0.35);
}
```

- [ ] **Step 3: Add House Brain logic to `js/admin.js`**

In `js/admin.js`, inside the `initAdmin()` function, append before the closing `}`:
```javascript
  // House Brain — Index Documents
  const hbBtn    = document.getElementById('hb-index-btn');
  const hbLog    = document.getElementById('hb-log');
  const hbStatus = document.getElementById('hb-status');
  let hbPollTimer = null;

  async function hbStartIndex() {
    hbBtn.disabled = true;
    hbLog.innerHTML = '';
    hbStatus.textContent = 'Starting…';
    try {
      const res = await fetch('/api/index', { method: 'POST' });
      const data = await res.json();
      if (res.ok) {
        hbPollTimer = setInterval(hbPollStatus, 2000);
      } else {
        hbStatus.textContent = data.error || 'Error starting index';
        hbBtn.disabled = false;
      }
    } catch {
      hbStatus.textContent = 'Server unreachable';
      hbBtn.disabled = false;
    }
  }

  async function hbPollStatus() {
    try {
      const res  = await fetch('/api/index/status');
      const data = await res.json();

      hbLog.innerHTML = (data.log || [])
        .map(l => `<span>${escAdminHtml(l)}</span>`)
        .join('');

      if (data.last_indexed && data.doc_count) {
        const d = new Date(data.last_indexed);
        const fmt = d.toLocaleDateString('en-NZ', { day:'numeric', month:'short', year:'numeric' });
        hbStatus.textContent = `Last indexed: ${fmt} · ${data.doc_count} documents`;
      }

      if (data.error) {
        hbStatus.textContent = `Error: ${data.error}`;
      }

      if (!data.running) {
        clearInterval(hbPollTimer);
        hbPollTimer = null;
        hbBtn.disabled = false;
        if (!data.error) hbStatus.textContent += ' ✓';
      }
    } catch {
      // server may be restarting — keep polling
    }
  }

  function escAdminHtml(str) {
    return String(str)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;');
  }

  hbBtn.addEventListener('click', hbStartIndex);

  // Show status on admin open
  hbPollStatus();
```

- [ ] **Step 4: Verify in browser**

1. Open `http://localhost:8080`
2. Open admin panel → "House Brain" section visible with "Index Documents" button
3. Click "Index Documents" → button disables, log lines appear ("Scanning PDFs…")
4. Wait for completion → "Last indexed: [date] · N documents ✓"
5. Open chat drawer → ask "What easements are on the title?" → answer cites Title & Easements PDF

- [ ] **Step 5: Commit**

```bash
git add index.html style.css js/admin.js
git commit -m "feat: admin panel House Brain section with Index Documents + live log"
```

---

## Verification Checklist

After all tasks complete, verify end-to-end:

- [ ] `cd backend && python app.py` → dashboard loads at `http://localhost:8080`
- [ ] Admin panel → "House Brain" section visible
- [ ] Click "Index Documents" → log scrolls with PDF names → "Complete ✓"
- [ ] Chat icon in controls → drawer slides in from left
- [ ] Ask "What is the legal description of the property?" → answer from `property.json`
- [ ] Ask "What easements are on the title?" → answer cites Title & Easements PDF
- [ ] Ask "How do I reset the dishwasher?" → answer cites appliance manual (if indexed)
- [ ] Press Escape → drawer closes
- [ ] Focus mode (H) → panels hidden → chat button still accessible
- [ ] No API keys in any committed file
