
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

##### Layout & navigation
- [ ] Collapse admin tools — move Re-index, Manage tags, Stats behind a single ⚙ menu to reduce toolbar clutter
- [ ] Welcome / empty state — show total docs, top companies, and example searches before the user has typed anything
- [ ] Improve result card hierarchy — make company and amount the hero text; filename secondary; larger thumbnail

##### Search experience
- [ ] Search-as-you-type — debounced (~400ms) so results appear without pressing Enter
- [ ] Keyboard shortcut — ⌘K focuses the search bar from anywhere in the app

## License

Private project for personal use.

Private project for personal use.
