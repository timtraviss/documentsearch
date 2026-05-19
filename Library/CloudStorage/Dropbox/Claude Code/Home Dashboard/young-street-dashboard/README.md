# 11 Young Street — Property Dashboard

A personal property dashboard for 11 Young Street, Scotts Landing, Mahurangi East, NZ. Built as a local web app: no build step, no npm, no bundler — plain HTML, CSS, and vanilla ES modules served by a Flask backend.

## How to run

### 1. Install Python dependencies

```bash
cd young-street-dashboard/backend
pip3 install -r requirements.txt
```

### 2. Configure API keys

Create `backend/.env` (gitignored):

```
ANTHROPIC_API_KEY=sk-ant-...
OPENAI_API_KEY=sk-...
DOCUMENTS_FOLDER=/path/to/your/11 Young Street/
PORT=8080
```

Create `config.js` in the dashboard root (gitignored):

```js
export const OPENWEATHER_KEY = 'your_openweather_key_here';
```

### 3. Start the server

```bash
cd backend && python3 app.py
```

Then open `http://localhost:8080`.

---

## What's built

### Map
- Full-screen interactive map (Leaflet.js 1.9.4) centred on the property at zoom 17
- Three tile layers: **Satellite** (Esri, default), **Standard** (OSM), **Topographic**
- Property marker with popup

### Floor plan viewer
- Toggle between map and floor plan via the 📐 button
- PDF pages converted to PNG via `convert-plans.py` (PyMuPDF), stored in `plans/`
- Pan and zoom with Leaflet CRS.Simple; keyboard arrow keys page through plans
- Page count stored in `property.json` — button hidden if no plans are present

### Theme
- Dark / light toggle with emerald green accent (`#34d399`)
- Frosted-glass panels using `backdrop-filter: blur()`
- Theme switch auto-swaps map layer; manual layer picks are respected

### Admin panel
- Slide-in panel (⚙ button) for theme, accent colour, opacity, blur, and vignette controls
- **House Brain** section: Index Documents button triggers background PDF scan + embedding build; shows live log and last-indexed timestamp

### Clock panel
- Live time and date, Auckland timezone, 24-hour format, Electrolize monospace font
- Sunrise / sunset times populated by the weather fetch

### Weather panel
- Current temperature, condition, feels-like, humidity, UV index, pressure
- Wind speed, direction, and gust with animated SVG compass rose
- 3-day forecast strip
- Source: OpenWeather API 2.5

### Tides panel
- Smooth cosine-interpolated SVG tide curve for the current Auckland day
- "Now" marker showing current position in the tide cycle
- Next tide callout: type, height, and countdown
- H/L table; past tides dimmed, next tide highlighted
- Source: NIWA CSV (`tides_31days_from_19May.csv`) — update periodically

### Property panel
Three tabs:

| Tab | Contents |
|-----|----------|
| Overview | Address, legal description, builder, build year, rates, valuations, utilities |
| Contacts | Trade/supplier contacts from `contacts.json`; live search; phone and email links |
| Documents | Link to the Dropbox `11 Young Street` folder |

All property data lives in `property.json`.

### House Brain (AI chat)
- Slide-in chat drawer (brain icon) powered by Claude (`claude-sonnet-4-6`)
- Answers questions about the property grounded in indexed documents (LIM, title, insurance, CoC, manuals)
- Vector search via FAISS + OpenAI embeddings (`text-embedding-3-small`) for relevant document excerpts
- Cites source documents in responses
- Live dashboard context (current weather, upcoming tides, time) sent with every query
- In-memory conversation history per session

---

## File structure

```
young-street-dashboard/
├── index.html
├── app.js
├── style.css
├── config.js              ← gitignored — OpenWeather key
├── property.json          ← all property data
├── contacts.json          ← trade/supplier contacts
├── tides_31days_from_19May.csv
├── convert-plans.py
├── fonts/
│   └── Electrolize-Regular.ttf
├── plans/                 ← generated PNG pages (gitignored)
├── backend/
│   ├── app.py             ← Flask server + API routes
│   ├── database.py        ← SQLite document store
│   ├── indexer.py         ← PDF scanner (mtime-based incremental)
│   ├── embeddings.py      ← FAISS vector index + OpenAI embeddings
│   ├── requirements.txt
│   ├── .env               ← gitignored — API keys + config
│   └── tests/
│       ├── test_database.py
│       ├── test_embeddings.py
│       └── test_indexer.py
└── js/
    ├── map.js
    ├── theme.js
    ├── floorplan.js
    ├── focus.js
    ├── state.js
    ├── admin.js
    ├── dashboard-context.js
    └── panels/
        ├── clock.js
        ├── weather.js
        ├── tides.js
        ├── property.js
        └── chat.js
```

---

## Tech stack

| Layer | Choice |
|-------|--------|
| Backend | Flask (Python) |
| AI / LLM | Anthropic `claude-sonnet-4-6` |
| Embeddings | OpenAI `text-embedding-3-small` |
| Vector search | FAISS (IndexFlatL2) |
| Document store | SQLite + FTS5 |
| PDF extraction | pdfminer.six |
| Map / floor plan | Leaflet.js 1.9.4 (CDN) |
| Weather | OpenWeather API 2.5 |
| Tides | NIWA CSV — cosine-interpolated SVG chart |
| Font | Electrolize (local TTF) |
| Styling | Vanilla CSS with custom properties |
| JS | Vanilla ES modules — no bundler |

---

## Indexing documents

1. Set `DOCUMENTS_FOLDER` in `backend/.env` to your folder of PDFs
2. Open the dashboard → admin panel (⚙) → **Index Documents**
3. Watch the live log — new files are indexed, unchanged files are skipped
4. Once complete, the House Brain can answer questions from those documents

Re-indexing is incremental: only new or modified PDFs are processed.

---

## Updating tide data

1. Go to [NIWA Tide Forecaster](https://tides.niwa.co.nz) — coordinates `-36.48, 174.734`, export as CSV
2. Replace `tides_31days_from_19May.csv` with the new file
3. Update `CSV_PATH` at the top of `js/panels/tides.js` to match the new filename

## Updating floor plans

```bash
# Place the PDF in the parent folder as 11_Young_Street_plans.pdf, then:
python3 convert-plans.py
```

---

## Future improvements

- **Mapbox** — custom dark map style matching the dashboard theme
- **Tide data automation** — script to fetch and replace the CSV on a schedule
- **Hosting** — deploy to a server for tablet access without a local machine running
- **LiveKit voice** — voice interface for the House Brain
- **PWA / offline** — Service Worker so the dashboard loads from cache
