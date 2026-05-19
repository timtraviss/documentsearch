# House Brain — AI Chat & Vector Search Design

## Goal

Add an AI-powered "brain for the house" to the 11 Young Street dashboard. Users can ask natural-language questions about the property — easements on the title, how to reset an appliance, what the LIM says about the site — and get answers grounded in the actual property documents, with source citations.

## Context

The dashboard is currently a vanilla JS static site served by `python3 -m http.server 8080`. It has no backend. To support document ingestion, vector search, and Claude API calls, we need a real backend server. Flask replaces the static server — it serves the dashboard files AND the AI API from a single process on the same port.

Architecture and UI decisions were validated through a visual brainstorming session on 2026-05-19.

---

## Architecture

### Stack
- **Backend**: Python Flask (reusing patterns from the Email Attachments Search project)
- **Vector store**: FAISS (`IndexFlatL2`) + metadata in SQLite
- **Full-text search**: SQLite FTS5 (fallback when embeddings not built)
- **Embeddings**: OpenAI `text-embedding-3-small` (1536-dimensional, 1600-char chunks, 200-char overlap)
- **LLM**: Anthropic `claude-sonnet-4-6`
- **PDF extraction**: `pdfminer.six`
- **Frontend**: Vanilla JS, no build step (unchanged constraint)

### Server startup

```bash
cd backend && python app.py
# Dashboard: http://localhost:8080
# API:       http://localhost:8080/api/...
```

Replaces `python3 -m http.server 8080`. Same URL in the browser.

### File structure

```
young-street-dashboard/
├── backend/                     ← new
│   ├── app.py                   Flask server + API routes + static file serving
│   ├── indexer.py               PDF scan → text extraction (pdfminer.six)
│   ├── embeddings.py            Chunking + OpenAI embeddings + FAISS index
│   ├── database.py              SQLite schema + FTS5 + document CRUD
│   ├── requirements.txt
│   ├── .env                     API keys (gitignored)
│   ├── house.db                 SQLite database (gitignored, generated)
│   └── house.faiss              FAISS vector index (gitignored, generated)
├── index.html                   + chat drawer HTML
├── app.js                       + initChat() import
├── style.css                    + chat drawer styles
├── js/
│   ├── panels/
│   │   └── chat.js              ← new — terminal-style chat drawer
│   └── ...
└── admin.js                     + House Brain section (index button + status)
```

---

## Backend

### API endpoints

| Route | Method | Purpose |
|-------|--------|---------|
| `/` | GET | Serves `index.html` (dashboard) |
| `/api/ask` | POST | Chat: vector search + Claude response |
| `/api/index` | POST | Trigger document indexing (background thread) |
| `/api/index/status` | GET | Poll indexing progress |

### POST /api/ask

**Request:**
```json
{
  "query": "What easements are on the title?",
  "messages": [
    { "role": "user", "content": "..." },
    { "role": "assistant", "content": "..." }
  ]
}
```

**Response:**
```json
{
  "answer": "Two easements are recorded...",
  "sources": [
    { "filename": "NA46B_820_Title_Search_Copy.pdf", "name": "Title & Easements", "snippet": "Schedule 4..." }
  ]
}
```

**Logic:**
1. FAISS search — top 6 chunks matching the query
2. Inject `property.json` facts as structured system context (address, rates, utilities, valuations, utilities)
3. Build Claude prompt: system context + document chunks + conversation history
4. Call `claude-sonnet-4-6`, return answer + deduplicated source list

### POST /api/index

Starts a background thread that:
1. Scans `DOCUMENTS_FOLDER` for `.pdf` files
2. Skips files unchanged since last index (mtime cache in SQLite)
3. Extracts text via `pdfminer.six`
4. Chunks to 1600 chars with 200-char overlap
5. Embeds via OpenAI `text-embedding-3-small`
6. Writes vectors to `house.faiss`, metadata to `house.db`

Returns immediately: `{ "status": "started" }`

### GET /api/index/status

Returns: `{ "running": bool, "progress": "12/15 documents", "log": [...], "error": null }`

### Configuration — `backend/.env`

```
ANTHROPIC_API_KEY=sk-ant-...
OPENAI_API_KEY=sk-...
DOCUMENTS_FOLDER=/Users/timothytraviss/Library/CloudStorage/Dropbox/11 Young Street/
PORT=8080
```

The existing `config.js` (OpenWeather key) is unchanged — client-side only.

---

## Frontend

### Chat drawer (`js/panels/chat.js`)

A full-height slide-in drawer from the **left** edge. Triggered by a new brain/chat icon button in the `.controls` bar.

**Terminal aesthetic:**
- Monospace font (`Electrolize`, matching the clock)
- Dark background (`rgba(4,8,12,0.98)`)
- `❯` prefix on user questions (accent colour)
- `→` bullets on AI list items
- Source cited inline as a single dim line below each answer: `─ Title & Easements · LINZ`
- `searching documents...` indicator while waiting

**Structure:**
```
┌─────────────────────────────┐
│ house-brain  ~/11-young-st  │  ← header bar
├─────────────────────────────┤
│                             │
│ ❯ What easements...?        │  ← user message
│   Two easements:            │  ← AI answer
│   → Right of way (Lot 10)   │
│   → Drainage, N boundary    │
│   ─ Title & Easements · LINZ│  ← source
│                             │
│ ❯ How do I reset the dish…  │
│   searching documents...    │
│                             │
├─────────────────────────────┤
│ ❯ _                         │  ← input, pinned bottom
└─────────────────────────────┘
```

**Behaviour:**
- Enter or click send to submit
- Conversation history persists for the session (in-memory array)
- Escape or close button collapses the drawer
- Drawer slides over the map (does not push panels aside)
- Works correctly with focus mode (panels hidden → drawer still opens)

### Admin panel — House Brain section

New section added to the existing `admin.js` / `#admin-panel`, below the Vignette toggle:

- **Index Documents** button — calls `POST /api/index`, polls `/api/index/status` every 2s
- Live log output (last 5 lines, monospace, small)
- Status line: "Last indexed: 19 May 2026 · 8 documents"
- While running: button disabled, spinner, log lines scrolling

### Controls bar

New `#btn-chat` button added to `.controls` (between floor plan and focus buttons). Icon: a terminal/brain SVG. Toggles the chat drawer open/closed.

---

## Data model

### `documents` table (SQLite)

```sql
id            INTEGER PRIMARY KEY
path          TEXT UNIQUE        -- absolute path on disk
filename      TEXT
name          TEXT               -- human name from property.json (if matched)
mtime         REAL               -- last modified time for incremental sync
text          TEXT               -- full extracted text
snippet       TEXT               -- first 200 chars
indexed_at    TEXT               -- ISO timestamp
```

### FAISS metadata (JSON sidecar)

Each vector in the FAISS index maps to:
```json
{ "doc_id": 42, "filename": "LIM.pdf", "name": "LIM Report", "chunk_index": 3, "snippet": "..." }
```

### property.json — no schema changes

`property.json` is injected as system context on every `/api/ask` call. The existing `documents[].url` fields are used to match indexed PDFs to their human-readable names. No new fields needed now. Future: add `"vector_id"` per document when cloud hosting requires explicit upload tracking.

---

## Cloud-ready design

The only environment-specific value is `DOCUMENTS_FOLDER` in `.env`. On a cloud server this points to an uploaded folder or S3-compatible bucket (with a thin adapter). All Flask routes, FAISS operations, SQLite queries, and Claude calls are identical. To deploy:

1. Set `DOCUMENTS_FOLDER` to cloud storage path
2. Set `PORT` to whatever the host requires
3. Upload `house.db` and `house.faiss` (or re-index on first run)

---

## Future phases

### Phase 2 — Voice (LiveKit)
Add a LiveKit agent that connects to the same `/api/ask` endpoint. Mic button appears in the chat drawer. Speak a question, get a spoken answer. The v1 REST API is the integration point — no changes to the core backend needed.

### Phase 3 — Hosted deployment
Move `DOCUMENTS_FOLDER` to cloud storage. Add auth (simple shared secret or Cloudflare Access). Deploy Flask to Railway or Render.

---

## Verification

1. `cd backend && python app.py` — dashboard loads at `http://localhost:8080`
2. Open admin panel → "Index Documents" button visible in House Brain section
3. Click Index → log shows PDFs being processed, completes without error
4. Click brain icon in controls → chat drawer slides in from left
5. Ask "What is the legal description of the property?" → answer includes lot number from `property.json`, no documents needed
6. Ask "What easements are on the title?" → answer cites Title & Easements PDF with snippet
7. Ask "How do I reset the Miele dishwasher?" → answer cites appliance manual
8. Press Escape → drawer closes
9. Enable focus mode (H) → map is clean, drawer still opens via button
