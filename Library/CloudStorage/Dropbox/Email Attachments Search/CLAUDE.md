# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Running the app

**From terminal (development):**
```bash
source venv/bin/activate
python backend/app.py
# Opens at http://localhost:5000 (auto-selects free port if 5000 is busy)
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
This copies `app.py`, `indexer.py`, `search.html`, static assets, and `app_launcher.py` into the bundle and clears cached `.pyc` files. Always run this after edits when testing via the .app.

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
1. `backend/indexer.py` walks `PDF_FOLDER`, extracts text via pdfminer, writes `backend/index.json` (each entry has `path`, `relative_path`, `filename`, `text`, `mtime`)
2. `backend/app.py` loads `index.json` into the global `documents` list at startup (in-memory for the lifetime of the process)
3. User tags are persisted to `~/Library/Application Support/Document Search/tags.json` — **outside** the bundle so rebuilds never wipe them
4. The Flask app serves `backend/templates/search.html` which is a single-page UI making JSON API calls

### Key backend files
- `backend/app.py` — Flask app; all routes; regex-based text extraction helpers (`extract_company`, `extract_date`, `extract_total_amount`, `extract_company_from_filename`); in-memory `documents` global updated after reindex
- `backend/indexer.py` — `scan_pdfs(folder, progress_callback, existing_index)`: pass `existing_index=documents` for incremental mode (skips files with matching mtime)
- `backend/embeddings.py` — optional OpenAI FAISS semantic search; only active when `vector.faiss` exists
- `app_launcher.py` — py2app entry point; finds a free port, starts Flask in a daemon thread, opens a pywebview window on the main thread

### Key frontend (search.html)
The entire UI is a single Jinja2 template with inline JS. Key globals:
- `_allResults` — full result array for the current search (used by sort and load-more)
- `_baseQueryStr` — query string of the active search (used to fetch more pages)
- `_selectedPaths` — Set of paths for bulk tagging
- `_pdfjsInit` — Promise that gates all PDF rendering (blob-URL worker for WKWebView compatibility)
- `PAGE_SIZE = 20` — results per page; load-more fetches next `offset`

Key functions: `performSearch(append)`, `buildQueryStr()`, `renderResultCards(docs, append)`, `sortResults(results)`, `viewPdf(path, filename)`, `renderPdfPage(pageNum)`.

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

### Configuration
`.env` file (at project root and bundled into the .app):
```
PDF_FOLDER=/path/to/Email Attachments
OPENAI_API_KEY=sk-...   # optional, enables semantic search
REINDEX_TOKEN=...        # optional, protects /reindex endpoint
```

### macOS bundle notes
- py2app bundles Python + all dependencies into `dist/Document Search.app`
- The bundle's Python is at `Contents/Resources/lib/python3.12/`
- `sync_bundle.sh` is the fast path for source-only changes; `setup.py py2app` is needed only for new packages
- macOS TCC (Full Disk Access) must be granted in System Settings for the .app to read files in `~/Library/CloudStorage/Dropbox/`
- Tags survive rebuilds because they're stored in `~/Library/Application Support/Document Search/tags.json`

DISTILLED_AESTHETICS_PROMPT = """
<frontend_aesthetics>
You tend to converge toward generic, "on distribution" outputs. In frontend design, this creates what users call the "AI slop" aesthetic. Avoid this: make creative, distinctive frontends that surprise and delight. Focus on:
 
Typography: Choose fonts that are beautiful, unique, and interesting. Avoid generic fonts like Arial and Inter; opt instead for distinctive choices that elevate the frontend's aesthetics.
 
Color & Theme: Commit to a cohesive aesthetic. Use CSS variables for consistency. Dominant colors with sharp accents outperform timid, evenly-distributed palettes. Draw from IDE themes and cultural aesthetics for inspiration.
 
Motion: Use animations for effects and micro-interactions. Prioritize CSS-only solutions for HTML. Use Motion library for React when available. Focus on high-impact moments: one well-orchestrated page load with staggered reveals (animation-delay) creates more delight than scattered micro-interactions.
 
Backgrounds: Create atmosphere and depth rather than defaulting to solid colors. Layer CSS gradients, use geometric patterns, or add contextual effects that match the overall aesthetic.
 
Avoid generic AI-generated aesthetics:
- Overused font families (Inter, Roboto, Arial, system fonts)
- Clichéd color schemes (particularly purple gradients on white backgrounds)
- Predictable layouts and component patterns
- Cookie-cutter design that lacks context-specific character
 
Interpret creatively and make unexpected choices that feel genuinely designed for the context. Vary between light and dark themes, different fonts, different aesthetics. You still tend to converge on common choices (Space Grotesk, for example) across generations. Avoid this: it is critical that you think outside the box!
</frontend_aesthetics>
"""