# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Running the app

**Frontend dev server (hot reload):**
```bash
cd frontend && npm run dev
# UI at http://localhost:5173 — proxies API calls to Flask on port 5001
```

**Backend (Flask):**
```bash
source venv/bin/activate
python backend/app.py
# API at http://localhost:5001
```

**Build frontend for production / bundle:**
```bash
cd frontend && npm run build
# Outputs to backend/static/ (index.html + assets/)
```

**As macOS .app bundle:**
```bash
open "dist/Document Search.app"
# Crashes write to dist/Document Search.app/Contents/Resources/error.log
```

**After editing source files, sync to the existing bundle without rebuilding:**
```bash
bash sync_bundle.sh
```
This builds the React frontend (`npm run build`), then copies `app.py`, `indexer.py`, the Vite output (`backend/static/`), and `app_launcher.py` into the bundle and clears cached `.pyc` files. Always run this after edits when testing via the .app.

**Full bundle rebuild (only needed when adding new Python packages):**
```bash
python setup.py py2app
```

**Index PDFs:**
```bash
python backend/indexer.py        # full index
# Incremental re-index is available via the UI's Re-index button
```

## Architecture

### Data flow
1. `backend/indexer.py` walks `PDF_FOLDER`, extracts text via pdfminer, writes to `backend/search.db` (SQLite + FTS5)
2. `backend/app.py` loads the SQLite index on each request (no in-memory global); text search uses FTS5
3. User tags are persisted to the same `search.db` in a `tags` table — path set via `DB_PATH` env var
4. Flask serves `backend/static/index.html` (Vite-built React app) at `/`; API routes handle all data

### Frontend stack
- **React 18 + TypeScript** via Vite (`frontend/`)
- **Mantine v7** — component library (AppShell, Modal, Drawer, Table, Select, etc.)
- **Framer Motion** — page-load stagger animations, AnimatePresence
- **pdfjs-dist** — PDF rendering in result cards and full-page viewer
- **@tabler/icons-react** — icon set
- **CSS variables** in `frontend/src/index.css` — `--page-bg`, `--card-bg`, `--ink`, `--border`, `--accent`
- Fonts: **DM Serif Display** (headings), **DM Mono** (filenames/code), **DM Sans** (body) via Google Fonts

### Key frontend files
- `frontend/src/App.tsx` — root component; all state management; results grid; modal/drawer wiring
- `frontend/src/api.ts` — typed wrappers for all Flask endpoints; exports `PAGE_SIZE = 20`
- `frontend/src/types.ts` — TypeScript interfaces (`SearchResult`, `DocumentTags`, `SearchFilters`, etc.)
- `frontend/src/theme.ts` — Mantine theme (primaryColor teal, fonts, ink-on-cream palette)
- `frontend/src/components/SearchBar.tsx` — search input, advanced filters collapse, Tools menu
- `frontend/src/components/ResultCard.tsx` — card with PDF thumbnail (pdfjs 0.5×), badges, actions
- `frontend/src/components/PdfModal.tsx` — full PDF viewer modal + tag editor drawer
- `frontend/src/components/BulkToolbar.tsx` — sticky bulk-tag bar (appears when docs are selected)
- `frontend/src/components/ReindexModal.tsx` — reindex with live log streaming
- `frontend/src/components/TagMgmt.tsx` — rename tag values across all documents
- `frontend/src/components/StatsPanel.tsx` — stats drawer with ring progress + bar charts
- `frontend/src/components/WelcomeState.tsx` — landing state with quick-search chips

### Key backend files
- `backend/app.py` — Flask app; all routes; serves React SPA at `/`; regex extraction helpers
- `backend/indexer.py` — `scan_pdfs(folder, progress_callback, existing_index)`: incremental mode skips files with matching mtime
- `backend/database.py` — SQLite/FTS5 helpers; `get_db_path()` honours `DB_PATH` env var
- `backend/embeddings.py` — optional OpenAI FAISS semantic search; only active when `vector.faiss` exists
- `app_launcher.py` — py2app entry point; finds a free port, starts Flask in a daemon thread, opens a pywebview window

### API endpoints
| Endpoint | Purpose |
|---|---|
| `GET /search` | Main search; params: `q`, `company`, `date`, `amount`, `mode`, `tag_type`, `tag_year`, `tag_untagged`, `limit`, `offset` |
| `POST /reindex` | Start background reindex; body: `{ incremental: bool }` |
| `GET /reindex/status` | Poll reindex progress: `running`, `logs`, `count`, `skipped`, `error` |
| `GET /pdf/<path:filename>` | Serve PDF file; returns 403 on macOS TCC PermissionError |
| `GET/POST /tags/<path:filename>` | Get/save tags for a document |
| `POST /bulk_tags` | Apply tags to multiple paths |
| `GET /tag_values` | Unique values per tag field with counts |
| `POST /rename_tag` | Rename a tag value across all documents |
| `GET /stats` | Doc count + last-indexed timestamp |
| `GET /stats/breakdown` | Counts by type, company, year |
| `GET /export/csv` | Download CSV of matching results (same params as `/search`, no pagination) |
| `GET /companies` | Sorted list of unique company names from tags |
| `GET /assets/<path>` | Serve Vite-built JS/CSS assets |

### Configuration
`.env` file (at project root and bundled into the .app):
```
PDF_FOLDER=/path/to/Email Attachments
DB_PATH=/absolute/path/to/backend/search.db   # required for bundle; optional in dev
OPENAI_API_KEY=sk-...   # optional, enables semantic search
REINDEX_TOKEN=...        # optional, protects /reindex endpoint
```

### macOS bundle notes
- py2app bundles Python + all dependencies into `dist/Document Search.app`
- The bundle's Python is at `Contents/Resources/lib/python3.12/`
- `sync_bundle.sh` builds the frontend then syncs everything — run this for all source changes
- `setup.py py2app` is needed only when adding new Python packages
- macOS TCC (Full Disk Access) must be granted in System Settings for the .app to read files in `~/Library/CloudStorage/Dropbox/`
- Tags survive rebuilds because `DB_PATH` points outside the bundle

DISTILLED_AESTHETICS_PROMPT = """
<frontend_aesthetics>
This app uses Mantine v7 with a custom ink-on-cream editorial theme. When making UI changes:

- **Component library**: Use Mantine components (Button, Modal, Drawer, Select, etc.) — don't reach for raw HTML elements when a Mantine component exists
- **Palette**: CSS variables `--page-bg` (#F5F0E8), `--card-bg` (#FEFCF8), `--ink` (#1A1A2E), `--accent` (#0D7377), `--border`. Primary colour is `teal`.
- **Typography**: DM Serif Display for headings (fontFamily: '"DM Serif Display", serif'), DM Mono for filenames/code, DM Sans for body. Avoid Inter/Roboto/Arial.
- **Motion**: Framer Motion for page-load stagger (see App.tsx). Keep animations subtle — opacity + y-offset, 0.2–0.4s duration.
- **Tone**: Editorial, calm, document-oriented. Not dashboard-flashy. Teal accents on warm cream.

Avoid generic AI-generated aesthetics:
- Overused font families (Inter, Roboto, Arial, system fonts)
- Clichéd color schemes (particularly purple gradients on white backgrounds)
- Predictable layouts and component patterns
</frontend_aesthetics>
"""
