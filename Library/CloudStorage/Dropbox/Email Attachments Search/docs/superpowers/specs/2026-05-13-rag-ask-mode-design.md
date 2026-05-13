# RAG Ask Mode — Design Spec
_Date: 2026-05-13_

## Overview

Add a conversational "Ask AI" mode to the Document Search app alongside the existing document search. Users can ask natural language questions about their PDFs, get synthesised answers with citations, and ask follow-up questions in the same session. The existing Search mode is untouched.

---

## Goals

- Answer lookup, comparison, and summary queries conversationally
- Show full source document cards for the most recent answer
- Support multi-turn follow-up questions within a session
- Improve underlying retrieval quality by switching from whole-document to chunked embeddings

## Non-Goals

- Obsidian / Markdown file export
- Persistent conversation history (across page reloads)
- Streaming responses (can be added later)

---

## Architecture

```
Frontend (React)
  SearchBar.tsx     ← add Search / Ask mode toggle (SegmentedControl)
  AskPanel.tsx      ← new: chat history, source cards, follow-up input
  App.tsx           ← new state: searchMode, askMessages
  api.ts            ← new ask() function
  types.ts          ← new Message, Source types

Backend (Flask)
  embeddings.py     ← rewrite: chunk docs before embedding
  app.py            ← new POST /ask endpoint

Storage
  vector.faiss      ← rebuilt after chunking change (one-time manual step)
  metadata.json     ← updated: one entry per chunk, not per doc
```

The `/search` endpoint and document grid are **unchanged**. Ask mode is a parallel path that shares the FAISS index.

```
Search mode:  query → FTS5 / FAISS → document cards        (unchanged)

Ask mode:     query + history
                → POST /ask
                → embed query (OpenAI text-embedding-3-small)
                → FAISS top-6 chunks
                → Claude claude-sonnet-4-6 synthesis
                → { answer, sources[] }
```

---

## Backend Changes

### 1. Chunking — `embeddings.py`

Replace the current whole-document embedding (first 2,000 chars → one vector) with overlapping chunk embeddings.

**Chunk parameters:**
- Chunk size: ~1,600 characters (~400 tokens)
- Overlap: 200 characters
- Each chunk → one embedding → one row in `metadata.json`

**Updated `metadata.json` entry shape:**
```json
{
  "path": "Contracts/Smith & Co Contract.pdf",
  "filename": "Smith & Co Contract.pdf",
  "chunk_index": 2,
  "snippet": "...text of this chunk (first 300 chars)..."
}
```

After this change, `vector.faiss` and `metadata.json` must be rebuilt:
```bash
source venv/bin/activate
python backend/embeddings.py
```

A **Rebuild Embeddings** button is added to the Re-index modal in the UI to make this accessible without the terminal.

### 2. `/ask` endpoint — `app.py`

```
POST /ask
Content-Type: application/json

Body:
{
  "query": "What are the key terms in the Smith contract?",
  "messages": [
    { "role": "user",      "content": "..." },
    { "role": "assistant", "content": "..." }
  ]
}

Response:
{
  "answer": "The Smith & Co service agreement includes...",
  "sources": [
    { "filename": "Smith & Co Contract.pdf",
      "path": "Contracts/Smith & Co Contract.pdf",
      "snippet": "...termination notice period..." },
    ...
  ]
}
```

**Endpoint logic:**
1. Embed `query` via OpenAI (`text-embedding-3-small`)
2. Search FAISS for top-6 chunks
3. Deduplicate sources — multiple chunks from the same PDF → one source entry (keep the highest-scoring chunk's snippet)
4. Build prompt (see below)
5. Call `claude-sonnet-4-6` via Anthropic SDK, passing conversation history + new user turn
6. Return `{ answer, sources }`

**Prompt design:**
```
System:
  You are a document assistant. Answer questions based only on the
  document excerpts provided. Cite documents by filename when relevant.
  If the answer is not in the provided excerpts, say so clearly.

[Prior conversation messages — role: user/assistant alternating]

User:
  Here are the relevant document excerpts:
  ---
  [Source: Smith & Co Contract.pdf]
  {chunk text}
  ---
  [Source: Smith Amendment 2024.pdf]
  {chunk text}
  ---

  Question: {query}
```

**Error handling:**
- FAISS not built → return `{ error: "Embeddings not built. Please rebuild embeddings." }`
- Anthropic API failure → return `{ error: "AI service unavailable. Please try again." }`
- Empty query → 400

**Environment:**
- `ANTHROPIC_API_KEY` — required for `/ask`; endpoint returns a clear error if missing
- `OPENAI_API_KEY` — still required for embeddings (unchanged)

---

## Frontend Changes

### 1. Mode toggle — `SearchBar.tsx`

Add a Mantine `SegmentedControl` above the search input with two segments:
- **Search documents** (default)
- **Ask AI**

Switching modes:
- Search → Ask: document results clear; AskPanel renders; SearchBar text input hidden (AskPanel provides its own input)
- Ask → Search: AskPanel hides; SearchBar text input visible again; conversation history preserved in state (not reset)

### 2. New types — `types.ts`

```ts
interface Message {
  role: 'user' | 'assistant';
  content: string;
  sources?: Source[];
}

interface Source {
  filename: string;
  path: string;
  snippet: string;
}

interface AskResponse {
  answer?: string;
  sources?: Source[];
  error?: string;
}
```

### 3. New API function — `api.ts`

```ts
export async function ask(query: string, messages: Message[]): Promise<AskResponse>
// POST /ask — returns answer + sources or error
```

### 4. New state — `App.tsx`

```ts
const [searchMode, setSearchMode] = useState<'search' | 'ask'>('search');
const [askMessages, setAskMessages] = useState<Message[]>([]);
```

- `searchMode` drives which panel renders (document grid vs AskPanel)
- `askMessages` is the conversation history, passed to `ask()` on each new message and updated with each response

### 5. AskPanel.tsx — new component

**Layout:**
```
┌──────────────────────────────────────────────────────┐
│  [chat history — scrollable]                         │
│                                                      │
│  You                                          10:42  │
│  What were the key terms in the Smith contract?      │
│                                                      │
│  Claude                                       10:42  │
│  The Smith & Co service agreement includes a         │
│  90-day termination notice, a monthly retainer       │
│  of $2,400, and an auto-renewal clause...            │
│                                                      │
│  ┌──────────────────┐  ┌──────────────────┐          │
│  │ [thumb] Smith &  │  │ [thumb] Smith    │          │
│  │ Co Contract.pdf  │  │ Amendment.pdf    │          │
│  │ [tags] [open]    │  │ [tags] [open]    │          │
│  └──────────────────┘  └──────────────────┘          │
│  ↑ full cards, most recent answer only               │
│                                                      │
│  You                                          10:45  │
│  What happens if they breach it?                     │
│  [Smith.pdf] [Smith Amendment.pdf]  ← collapsed      │
│                                                      │
│  Claude  ● ● ●                                       │
│                                                      │
└──────────────────────────────────────────────────────┘
┌──────────────────────────────────────────────────────┐
│  Ask a follow-up...               [New chat]  [↵]   │
└──────────────────────────────────────────────────────┘
```

**Behaviour:**
- Source cards — use the existing `ResultCard` component; appear below the most recent assistant message only
- Earlier assistant messages — sources collapse to small inline badges (filename only, clickable → PdfModal)
- Loading state — three-dot pulse animation while awaiting `/ask` response
- Error state — inline error message inside a chat bubble (not a toast)
- New chat button — clears `askMessages` state only; mode stays as Ask
- Auto-scrolls to bottom on each new message

**Styling:** follows existing ink-on-cream theme (CSS variables `--page-bg`, `--card-bg`, `--ink`, `--accent`). User bubbles right-aligned, Claude bubbles left-aligned with a subtle `--card-bg` background.

---

## Re-index Modal Addition

Add a **Rebuild Embeddings** button to the existing `ReindexModal.tsx`. Triggers a new `POST /rebuild-embeddings` endpoint that runs `create_vector_db()` in a background thread and streams progress via Server-Sent Events, matching the existing `/reindex` + `/reindex/status` pattern exactly. The modal log area shows per-document embedding progress and a final count on completion.

---

## Setup After Implementation

1. Install `anthropic` package:
   ```bash
   source venv/bin/activate
   pip install anthropic
   ```
2. Add to `requirements.txt`
3. Confirm `ANTHROPIC_API_KEY` is set in `.env`
4. Rebuild embeddings (one-time):
   ```bash
   python backend/embeddings.py
   ```
5. Bundle: run `python setup.py py2app` once to include the new `anthropic` package in the `.app`

---

## Data Flow Summary

```
User types question in AskPanel
  → append to askMessages as { role: 'user', content: query }
  → POST /ask { query, messages: askMessages }
    → embed query (OpenAI)
    → FAISS top-6 chunks
    → deduplicate sources
    → Claude claude-sonnet-4-6 with system prompt + chunks + history
  → { answer, sources }
  → append to askMessages as { role: 'assistant', content: answer, sources }
  → re-render AskPanel: full cards on latest message, badges on prior messages
```

---

## Files Changed

| File | Change |
|------|--------|
| `backend/embeddings.py` | Rewrite `create_vector_db()` to chunk before embedding |
| `backend/app.py` | Add `POST /ask` and `POST /rebuild-embeddings` endpoints |
| `frontend/src/types.ts` | Add `Message`, `Source`, `AskResponse` |
| `frontend/src/api.ts` | Add `ask()` function |
| `frontend/src/App.tsx` | Add `searchMode`, `askMessages` state; render AskPanel |
| `frontend/src/components/SearchBar.tsx` | Add mode toggle (SegmentedControl) |
| `frontend/src/components/AskPanel.tsx` | New file — full chat component |
| `frontend/src/components/ReindexModal.tsx` | Add Rebuild Embeddings button |
| `requirements.txt` | Add `anthropic` |
| `setup.py` | Add `anthropic` to py2app packages list |
