# 11 Young Street — Property Dashboard

A personal property dashboard for 11 Young Street, Scotts Landing, Mahurangi East, NZ. Built as a local web app: no build step, no npm, no server required beyond serving ES modules.

## How to open

**Requires a local server** (ES modules + `fetch()` don't work on `file://`):

```bash
cd young-street-dashboard
python3 -m http.server 8080
```

Then open `http://localhost:8080`.

**API key:** Create `config.js` in the dashboard root (gitignored):

```js
export const OPENWEATHER_KEY = 'your_key_here';
```

---

## What's built

### Map
- Full-screen interactive map (Leaflet.js 1.9.4) centred on the property at zoom 17
- Three tile layers switchable via bottom-right control:
  - **Satellite** — Esri World Imagery (default)
  - **Standard** — OpenStreetMap
  - **Topographic** — OpenTopoMap
- Property marker with popup

### Floor plan viewer
- Toggle between map and floor plan via the 📐 button (top-right)
- PDF pages converted to PNG via `convert-plans.py` (PyMuPDF) and stored in `plans/`
- Pan and zoom with Leaflet CRS.Simple; keyboard arrow keys page through plans
- Page count stored in `property.json` — the toggle button is hidden if no plans are present

### Theme
- Dark / light toggle (top-right button)
- Emerald green accent (`#34d399`) throughout
- Frosted-glass panels using `backdrop-filter: blur()`
- Theme switch auto-swaps map layer; manual layer picks are respected

### Clock panel (top-left)
- Live time and date, Auckland timezone, 24-hour format
- Electrolize monospace font
- Sunrise / sunset times shown with SVG icons — populated by the weather fetch

### Weather panel (top-right)
- Current temperature, condition (emoji + label), feels-like, humidity, cloud cover
- UV index and pressure
- Wind speed, direction, and gust — with an animated SVG compass rose
- 3-day forecast strip
- Data source: OpenWeather API 2.5 (key required in `config.js`)

### Tides panel (top-right, below weather)
- Smooth cosine-interpolated SVG tide curve for the current Auckland day
- "Now" marker (white dot + dashed line) showing current position in the tide cycle
- Next tide callout: type, height, and countdown
- Compact H/L table below the chart; past tides dimmed, next tide highlighted
- Data source: NIWA CSV (`tides_31days_from_19May.csv`) — update this file periodically

### Property panel (bottom-left)
Three tabs:

| Tab | Contents |
|-----|----------|
| Overview | Address, legal description, builder, build year, rates details, valuations, utilities |
| Contacts | Trade/supplier contacts from `contacts.json`; live search; phone and email links |
| Documents | Link to the Dropbox `11 Young Street` folder |

All property data lives in `property.json` — edit it there, not in the code.

---

## File structure

```
young-street-dashboard/
├── index.html
├── app.js
├── style.css
├── config.js              ← gitignored — add your OpenWeather key here
├── property.json          ← all property data
├── contacts.json          ← trade/supplier contacts
├── tides_31days_from_19May.csv  ← NIWA tide data (refresh periodically)
├── convert-plans.py       ← converts PDF floor plans to plans/*.png
├── fonts/
│   └── Electrolize-Regular.ttf
├── plans/                 ← generated PNG pages (gitignored)
│   └── page-01.png …
└── js/
    ├── map.js
    ├── theme.js
    ├── floorplan.js
    └── panels/
        ├── clock.js
        ├── weather.js
        ├── tides.js
        └── property.js
```

---

## Tech stack

| Layer | Choice |
|-------|--------|
| Map / floor plan | Leaflet.js 1.9.4 (CDN) |
| Weather | OpenWeather API 2.5 (key required) |
| Tides | NIWA CSV — cosine-interpolated SVG chart |
| Font | Electrolize (local TTF) |
| Styling | Vanilla CSS with custom properties |
| JS | Vanilla ES modules — no bundler |
| Hosting | Local server (`python3 -m http.server`) |

---

## Updating tide data

1. Go to [NIWA Tide Forecaster](https://tides.niwa.co.nz) — use coordinates `-36.48, 174.734`, export as CSV
2. Replace `tides_31days_from_19May.csv` with the new file
3. Update the `CSV_PATH` constant at the top of `js/panels/tides.js` to match the new filename

## Updating floor plans

```bash
# Place the PDF in the parent folder as 11_Young_Street_plans.pdf, then:
python3 convert-plans.py
```

This exports each page to `plans/page-XX.png` and updates `property.json` with the page count.

---

## Future improvements

- **Mapbox** — custom dark map style matching the dashboard theme; sharper satellite imagery
- **Persistent theme** — save last-chosen theme to `localStorage`
- **Tide data automation** — script to fetch and replace the CSV on a schedule
- **Documents tab** — links or previews for LIM, title, DRH warranty, insurance summary
- **Hosting** — deploy to Vercel/Netlify/Cloudflare Pages for tablet access without a local server
- **AI chat panel** — Claude API for property Q&A (maintenance history, supplier lookups)
- **PWA / offline** — Service Worker so the dashboard loads from cache without internet
