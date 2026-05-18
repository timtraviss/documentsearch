# 11 Young Street — Property Dashboard

A personal property dashboard for 11 Young Street, Scotts Landing, Mahurangi East, NZ. Built as a local web app: no build step, no npm, no server required.

## How to open

**Safari:** Open `index.html` directly from Finder — ES modules work on `file://`.

**Chrome / other browsers:** ES modules require a local server:

```bash
cd young-street-dashboard
python3 -m http.server 8080
```

Then open `http://localhost:8080`.

---

## V1 — What was built

### Map
- Full-screen interactive map (Leaflet.js 1.9.4) centred on the property
- Three tile layers switchable via bottom-right control:
  - **Satellite** — Esri World Imagery (default in dark mode)
  - **Standard** — OpenStreetMap (default in light mode)
  - **Topographic** — OpenTopoMap
- Property marker with popup

### Theme
- Dark / light toggle (top-right ☀️ / 🌙 button)
- Emerald green accent (`#34d399`) throughout
- Frosted-glass panels using `backdrop-filter: blur()`
- Theme switch auto-swaps map layer (satellite ↔ standard); manual layer picks are respected and skip the next auto-swap

### Clock panel (top-left)
- Live time and date, Auckland timezone
- Sunrise / sunset times populated by the weather fetch (Open-Meteo, already NZ local time — parsed with regex to avoid browser timezone bugs)

### Weather panel (top-right)
- Current temperature, WMO weather condition (emoji + label), wind speed (km/h)
- 3-day forecast strip (icon, high/low temps)
- Data source: Open-Meteo API — free, no key required
- Graceful degradation: shows "Weather unavailable" if the fetch fails

### Tides panel (bottom-left)
- Static reference tides for Mahurangi (H/L times and heights)
- Clearly labelled as approximate; placeholder for future live NIWA data

### Property panel (bottom-left, below tides)
Three tabs:

| Tab | Contents |
|-----|----------|
| Overview | Address, builder (David Reid Homes), and placeholder fields (build year, section, floor area, rates ref) |
| Contacts | 27 trade/supplier contacts loaded from `contacts.json`; live search filter by trade, company, or name; phone `tel:` links and email `mailto:` links |
| Documents | Reserved — placeholder text |

### Responsive layout
- Desktop: map fills screen, panels float over it
- Mobile (≤ 640 px): map pinned to 50 vh, panels stack below in a scrollable page

---

## Tech stack

| Layer | Choice |
|-------|--------|
| Map | Leaflet.js 1.9.4 (CDN) |
| Weather | Open-Meteo API (free, no key) |
| Tides | Static data (live NIWA API planned) |
| Styling | Vanilla CSS with custom properties |
| JS | Vanilla ES modules — no bundler |
| Hosting | Local file / any static host |

---

## Future improvements

### Live tides
NIWA's Tide API requires a key and does not support direct browser requests (CORS). A lightweight server-side proxy (e.g. a Cloudflare Worker or Vercel function) is needed to fetch and relay tide data. Store the key in `.env` (see `.env.example`).

### Persistent theme preference
Save the user's last-chosen theme to `localStorage` so it survives page reloads.

### Property overview — fill in the blanks
Once confirmed, populate: build year, section area, floor area, Auckland Council rates reference number, and LIM/title links.

### Documents tab
Add links or embedded previews for: council LIM, title documents, DRH warranty, Healthy Homes compliance certificate, insurance policy summary.

### Live contacts
Replace the static `contacts.json` with a small managed data source (e.g. a private Google Sheet via Apps Script, or a JSON file hosted in Dropbox with a public link) so contacts can be updated without touching code.

### Hosting
Deploy to a static host (Vercel, Netlify, Cloudflare Pages) for tablet/phone access without running a local server. Keep it private (password or IP allow-list).

### Tide graph
Replace the tabular tide display with a 24-hour curve chart (Chart.js or a small SVG path) once the live API proxy is in place.

### AI chat panel
A floating chat interface connected to Claude API for property-related Q&A (maintenance history, supplier lookups, council queries). Requires a backend for the API key.

### Weather extras
- Rainfall amount (mm) from Open-Meteo `precipitation` field
- UV index
- Wind direction (compass bearing)

### Offline / PWA
Add a Service Worker and web app manifest so the dashboard loads from cache when the internet is unavailable.
