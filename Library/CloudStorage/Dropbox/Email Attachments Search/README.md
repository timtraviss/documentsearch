
# Email Attachments Search

An AI-powered web application to search and quickly locate PDF invoices in your `Email Attachments` folder. The app provides both keyword-based and semantic AI search, with direct links and previews.

## Features

✨ **Dual Search Modes**
- **Text Search**: Fast keyword matching (always available)
- **AND/OR Filter Mode**: When using advanced filters (company, date, amount) you can toggle between matching all criteria or any criteria via the checkbox in the UI
- **Semantic AI Search**: Understanding query intent and content meaning (requires OpenAI API key)

📎 **Document Management**
- Automatic PDF scanning and indexing
- Text extraction from all PDFs
- Metadata tracking (filename, path)

🔍 **Smart UI**
- Clean, intuitive search interface
- Result snippets for quick preview
- Direct links to open/download PDFs
- Responsive design

## Quick Start

### 1. Install Dependencies

```bash
cd '/Users/timothytraviss/Library/CloudStorage/Dropbox/Email Attachments Search'
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. Configure Environment

Copy `.env.example` to `.env` and update values:

```bash
cp .env.example .env
```

Edit `.env`:
```env
OPENAI_API_KEY=sk-...  # (optional, for AI-powered semantic search)
PDF_FOLDER=/Users/timothytraviss/Library/CloudStorage/Dropbox/Email Attachments
```

### 3. Index PDF Documents

```bash
python backend/indexer.py
```

This scans your PDF folder and creates `backend/index.json` with extracted text from all documents.

### 4. Generate Embeddings (Optional)

For semantic AI-powered search, you'll need an OpenAI API key:

```bash
python backend/embeddings.py
```

This creates `backend/vector.faiss` (vector database) and `backend/metadata.json`.

### 5. Run the Web App

```bash
python backend/app.py
```

Open your browser to **http://localhost:5000**

### 6. (Optional) Build a macOS Application Bundle

To create a standalone `.app` that can be double-clicked to launch:

```bash
python setup.py py2app
```

The built app will be in `dist/Document Search.app`. You can move it to `/Applications` or run it directly. The app will:

- Start the Flask server automatically when opened
- Open your default browser to the application
- Run the server in the background (no terminal window)

The launcher now tries to bind to **5000** by default but will automatically fall back to any free port if 5000 is occupied.
You’ll see a console message such as:

```
Port 5000 unavailable, using 5003 instead.
```

You can still override this with the `PORT` environment variable if you prefer a specific port:

```bash
export PORT=5001   # preferred port
open dist/Document\ Search.app
```

Running `python backend/app.py` from the command line also uses the same auto‑selection logic. The bundle avoids crashing on port conflicts and prints any startup errors to stderr (visible in Terminal if you launch the app from there).

If the app does crash for some other reason when launched from Finder, a stack trace will be appended to `dist/Document Search.app/Contents/Resources/error.log` – open that file in a text editor to see the details. You can also start the app from a Terminal window to see output in real time.

## Usage

### Text Search
Enter keywords like:
- `invoice 12345`
- `acme corp`
- `pending`
- `2025-03-02`

### Sidebar & Help
Click the **Info** button (top‑right) or press `⌘/Ctrl+F` and then `☰` to open the sidebar. It shows
- keyboard shortcuts
- current app version

**Change history lives here in the README**; the on‑screen sidebar no longer displays it. Update this file whenever you make modifications.


You can also add query parameters for advanced filtering. Examples:

- `/search?q=invoice&company=acme`
- `/search?q=&date=2024&amount=1000-5000&mode=or`  *(mode can be `and` or `or`)*

### Semantic Search (with embeddings)
Ask natural questions:
- "Show me invoices from March"
- "Find unpaid bills"
- "Vendor Johnson and Associates"
- "Amount over 5000"

## File Structure

```
Email Attachments Search/
├── backend/
│   ├── app.py                 # Flask web app
│   ├── indexer.py             # PDF scanner & text extractor
│   ├── embeddings.py          # AI embeddings & vector search
│   ├── create_embeddings.sh   # Helper script
│   ├── index.json             # Indexed documents (generated)
│   ├── vector.faiss           # Vector database (generated)
│   ├── metadata.json          # Metadata index (generated)
│   ├── templates/
│   │   └── search.html        # Web UI
│   └── static/                # CSS/JS assets
├── .env                       # Configuration (create from .env.example)
├── requirements.txt           # Python dependencies
└── README.md                  # This file
```

## Configuration

### Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `OPENAI_API_KEY` | ❌ No | OpenAI API key for semantic search (get from [openai.com](https://platform.openai.com/api-keys)) |
| `PDF_FOLDER` | ✅ Yes | Path to your Email Attachments folder |

## Troubleshooting

### "PDF_FOLDER not configured or does not exist"
- Check that `PDF_FOLDER` in `.env` points to a valid directory
- Verify the folder contains PDF files

### Semantic search not working
- Ensure `OPENAI_API_KEY` is set in `.env`
- Run `python backend/embeddings.py` to generate vector database
- Check that `backend/vector.faiss` exists

### PDF preview not loading
- Verify the PDF file still exists in the original folder
- Check file permissions

## Development

### Automation / Scheduled Tasks

If you have a weekly script or coworker skill that scans the folder or relies on
file names, update it to work with the latest workflow:

1. **Don't hard‑code file names.** The renaming process (see rename_pdfs.py)
   may change names to `<Company>_<YYYY-MM-DD>.pdf`. Instead, consume the
   `backend/index.json` index which is kept in sync whenever you run the
   renamer or the indexer.
2. **Rebuild the index each run.** A simple cron/Task Scheduler entry can run:

    ```bash
    source venv/bin/activate
    python backend/indexer.py          # updates index.json
    python backend/embeddings.py  # optional, rebuild vectors
    ```

3. **Trigger renaming periodically.** If you want the weekly job to perform
   renaming first (useful for new incoming attachments), include:

    ```bash
    python backend/rename_pdfs.py --dry-run   # preview
    python backend/rename_pdfs.py             # apply and rebuild
    ```

4. **Use the index for searches.** Any consumer (web UI or other tool) can
   read and filter the JSON documents rather than walking the filesystem, so
   path changes are transparent.

Keeping the scheduler pointed at the index ensures no manual adjustments are
needed when filenames change.

## Development

### Updating after adding new PDFs
Simply re-run the indexer:
```bash
python backend/indexer.py
python backend/embeddings.py  # if using AI search
```

### Extending the app
- **Add filters**: Modify `app.py` search routes
- **Custom UI**: Edit `backend/templates/search.html`
- **Vector search tuning**: Adjust parameters in `embeddings.py`

## Technology Stack

- **Backend**: Python 3 + Flask
- **PDF Processing**: pdfminer.six
- **Vector Search**: FAISS (Facebook AI Similarity Search)
- **AI Embeddings**: OpenAI API
- **Frontend**: HTML5 + Vanilla JavaScript

## Roadmap

### In progress / recently completed
- [x] PDF thumbnail previews on result cards
- [x] Multi-page PDF viewer with Prev/Next navigation
- [x] Search term highlighting in result snippets
- [x] Company autocomplete in tag editor (populated from existing tags)
- [x] Tag system: Type, Company, Year badges on result cards
- [x] Document count and last-indexed date in header
- [x] Re-index with live progress log

### Planned improvements

#### Search quality
- [x] Sort results — by date (newest/oldest), company, year, or relevance
- [x] Untagged filter — quick toggle to show only documents with no tags
- [x] Increase results limit beyond 20 (pagination or "load more")

#### Tagging workflow
- [x] Auto-suggest tags — pre-fill company and year from extracted document text when opening a new document
- [x] Bulk tagging — select multiple results with checkboxes and apply tags to all at once
- [x] Tag management page — rename or merge tags across all documents

#### Performance
- [x] Incremental re-indexing — only process new/changed files (compare mtimes against index)
- [x] Background indexing — don't block the UI while indexing runs

#### Export / reporting
- [x] CSV export — export current search results with tags to a spreadsheet
- [x] Stats dashboard — breakdown of documents by company, type, and year

#### UI/UX redesign

##### Visual design
- [x] Distinctive color scheme with CSS variables — warm parchment palette (burnt sienna accent, ink tones)
- [x] Typography upgrade — Playfair Display for headings, IBM Plex Mono for filenames/amounts, Instrument Sans for UI
- [x] Atmospheric background — subtle dot-grid texture over warm parchment base
- [x] Page-load animation — staggered fadeUp reveal of header and search bar
- [x] Migrate UI to React + TypeScript + Mantine v7 — ink-on-cream editorial theme, DM Serif Display + DM Mono fonts, Framer Motion stagger animations

##### Layout & navigation
- [x] Collapse admin tools — Re-index, Manage tags, Stats behind a single ⚙ Tools dropdown
- [x] Welcome / empty state — doc count, last-indexed date, top company chips, and example search chips
- [x] Improve result card hierarchy — company + amount as hero text; type/year badges; filename secondary in monospace
- [x] Bulk tag toolbar — sticky bar with type/company/year fields appears when cards are selected; applies to all selected docs at once

##### Search experience
- [ ] Search-as-you-type — debounced (~400ms) so results appear without pressing Enter
- [ ] Keyboard shortcut — ⌘K focuses the search bar from anywhere in the app

## Scale & Evernote Migration Roadmap

The current architecture stores all document text in a flat `index.json` file loaded entirely into RAM, and searches via a linear scan. This works well up to ~500 PDFs but will become slow and memory-heavy beyond that.

**Practical thresholds:**
| Volume | Current app |
|---|---|
| ~500 PDFs | Works fine |
| 1,000–3,000 PDFs | Slow startup, sluggish search |
| 5,000+ PDFs | Memory pressure, search timeouts |

### Storage layer
- [x] Migrate `index.json` to SQLite — query documents on demand instead of loading all text into RAM at startup
- [x] Migrate `tags.json` to a SQLite table — avoid full-file rewrites on every tag save
- [x] Enable SQLite FTS5 full-text search — proper inverted index replaces the current linear scan (`for doc in documents`)

### Evernote import
- [ ] Write an `.enex` importer — Evernote exports XML (`.enex`), not PDFs; the current indexer only handles `.pdf` files
- [ ] Preserve Evernote metadata — notebooks, note-level tags, created/modified dates are richer than the current type/company/year schema
- [ ] Extend the tag schema to accommodate Evernote's notebook and tag hierarchy

### Performance
- [ ] Lazy-load document text — store snippets/metadata in memory; fetch full text from SQLite only when needed
- [ ] Index in parallel — use a worker pool in `indexer.py` for large initial imports (thousands of documents)

---

## SQLite Migration Plan

### Overview

Replace `index.json` + `tags.json` with a single SQLite database (`backend/search.db`). The DB lives in the Dropbox project folder so it is automatically cloud-backed-up. The Flask API and frontend do not change.

### Step 1 — `backend/database.py` *(new file)*
- [x] Schema + connection helpers. Nothing else changes yet.
- `documents` table with full `text` column + generated `snippet`
- `documents_fts` FTS5 virtual table (`content=documents`, `tokenize="unicode61"`)
- `tags` table replacing `tags.json`
- Helper functions: `get_db_path()`, `get_connection()`, `init_db()`, `upsert_document()`, `delete_missing_documents()`, `fts_rebuild()`, `get_tag()`, `upsert_tag()`, `upsert_tags_bulk()`

### Step 2 — `backend/migrate.py` *(new file)*
- [x] One-time script, run by hand after Step 1.
- Reads existing `index.json` → inserts all docs into DB
- Reads existing `tags.json` → inserts all tags into DB
- Calls `fts_rebuild()` once at end
- Keeps JSON files intact as rollback option until Step 5

### Step 3 — `backend/indexer.py`
- [x] Add `save_index_to_db(conn, docs)` alongside the existing `save_index()` (JSON)
- Mtime check moves from dict lookup to `SELECT mtime FROM documents WHERE relative_path = ?`
- After full scan: call `delete_missing_documents()` to prune stale rows, then `fts_rebuild()`
- Keep `save_index()` temporarily until Step 5

### Step 4 — `backend/app.py` *(largest change)*
- [x] Remove global `documents` list — all queries hit the DB via Flask `g`-based connection
- [x] Replace `load_tags()` with per-request DB queries
- [x] Replace `text_search()` linear scan with FTS5 `MATCH` query (with `highlight()` for snippets)
- [x] Update all tag write routes (`save_doc_tags`, `bulk_tags`, `rename_tag`) to use `upsert_tag()`
- [x] Update `stats()` and `debug_info()` to use `SELECT COUNT(*) FROM documents`
- [x] Reindex background thread opens its own DB connection (cannot use Flask `g`)

**Key gotchas:**
- FTS5 + `INSERT OR REPLACE` orphans old FTS rows — use explicit `UPDATE`/`INSERT` for existing docs, not upsert
- Flask threading: one connection per request via `g`; never use a module-level connection singleton
- FTS5 `MATCH` raises `MatchError` on malformed queries — wrap in try/except and fall back to `LIKE`

### Step 5 — Cleanup *(after Step 4 verified working)*
- [x] Remove `INDEX_FILE`, `save_index()`, `TAGS_FILE`, `load_tags()` from `app.py` and `indexer.py`
- [x] Delete `backend/index.json` (backup kept at `backend/index.json.bak`)
- [x] Delete `tags.json` from Application Support (already in DB)
- [x] Update `sync_bundle.sh` to copy `database.py` and clear its `.pyc` cache
- [x] Add `backend.database` to `includes` in `setup.py`
- [x] Fix py2app bundle: copy `sqlite3` stdlib package + `_sqlite3.so` extension into bundle (py2app omits both; `sync_bundle.sh` now handles this automatically)

### Backup note
The DB is stored in the Dropbox project folder (`backend/search.db`), giving automatic cloud backup and Dropbox version history. Tags were previously stored in `~/Library/Application Support/` with no backup.

## Version History

- **v0.5** — 2026-03-12 19:10 — Use Fugaz One font for "Document Search" h1 to match the app icon
- **v0.4** — 2026-03-12 18:45 — Fix bulk tag payload (spread tag fields to top level); fix PDF modal not rendering (keep canvas always mounted so ref is valid on first load)
- **v0.3** — 2026-03-12 18:04 — Complete React + Mantine v7 migration (Phases 1–5): TypeScript/Vite frontend, ink-on-cream editorial theme, BulkToolbar, Flask serving built SPA, updated sync_bundle.sh and CLAUDE.md
- **v0.2** — 2026-03-12 12:15 — Fix py2app bundle DB path via `DB_PATH` env var; add `.env` sync to `sync_bundle.sh`; add version bumping and timestamp to `/ship` skill
- **v0.1** — Initial release — SQLite + FTS5 migration replacing flat JSON files

## License

Private project for personal use.
