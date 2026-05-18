# 11 Young Street Property Dashboard — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a full-screen property dashboard for 11 Young Street that opens in a browser with no build step — Leaflet map as canvas, frosted-glass panels for clock, weather, tides, and property contacts.

**Architecture:** Vanilla HTML/CSS/JS with ES modules. Each panel is a self-contained file in `js/panels/` that owns its DOM and data fetching. `app.js` imports and initialises everything. CSS custom properties on `[data-theme]` handle theming — `theme.js` just swaps the attribute.

**Tech Stack:** HTML5, CSS3 (custom properties, backdrop-filter), Vanilla JS (ES modules), Leaflet.js 1.9.4 via CDN, Open-Meteo API (free, no key required)

---

## Important: Serving the Dashboard

ES modules do not work over `file://` URLs in Chrome. After each task, serve the project with:

```bash
cd "/path/to/Home Dashboard/young-street-dashboard"
python3 -m http.server 8080
```

Then open `http://localhost:8080`. Safari on macOS can open `index.html` directly without a server.

---

## File Map

| File | Responsibility |
|------|----------------|
| `index.html` | Page skeleton, CDN links, panel containers |
| `style.css` | All styles: layout, panels, themes, responsive |
| `app.js` | Entry point: imports and initialises map + panels |
| `contacts.json` | Supplier data (27 entries, copy of parent file) |
| `.env.example` | Placeholder for future NIWA tide API key |
| `js/map.js` | Leaflet setup, 3 base layers, marker + popup |
| `js/theme.js` | Dark/light toggle, default-layer switching |
| `js/panels/clock.js` | Live clock, Auckland date, sunrise/sunset display |
| `js/panels/weather.js` | Open-Meteo fetch, current conditions + 3-day forecast |
| `js/panels/tides.js` | Static approximate tide table, labelled clearly |
| `js/panels/property.js` | Tabbed panel: Overview, Contacts (with filter), Documents |

---

## Task 1: Project Scaffold

**Files:**
- Create: `young-street-dashboard/index.html`
- Create: `young-street-dashboard/style.css`
- Create: `young-street-dashboard/app.js`
- Create: `young-street-dashboard/contacts.json`
- Create: `young-street-dashboard/.env.example`
- Create: `young-street-dashboard/js/map.js`
- Create: `young-street-dashboard/js/theme.js`
- Create: `young-street-dashboard/js/panels/clock.js`
- Create: `young-street-dashboard/js/panels/weather.js`
- Create: `young-street-dashboard/js/panels/tides.js`
- Create: `young-street-dashboard/js/panels/property.js`

- [ ] **Step 1: Create the folder structure**

```bash
cd "/path/to/Home Dashboard"
mkdir -p young-street-dashboard/js/panels
```

- [ ] **Step 2: Copy contacts.json into the project**

```bash
cp contacts.json young-street-dashboard/contacts.json
```

- [ ] **Step 3: Create .env.example**

```bash
# .env.example
# Future: NIWA Tide API key (requires a server-side proxy — cannot be exposed in client JS)
# NIWA_API_KEY=your_key_here
```

- [ ] **Step 4: Create index.html**

```html
<!DOCTYPE html>
<html lang="en" data-theme="dark">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>11 Young Street</title>
  <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
  <link rel="stylesheet" href="style.css">
</head>
<body>

  <div id="map"></div>

  <header class="top-bar">
    <div id="panel-clock" class="panel"></div>
    <h1 class="property-title">11 Young Street</h1>
    <div class="top-right">
      <button id="theme-toggle" class="theme-btn" aria-label="Toggle theme">☀️</button>
      <div id="panel-weather" class="panel"></div>
    </div>
  </header>

  <div class="bottom-left">
    <div id="panel-tides" class="panel"></div>
    <div id="panel-property" class="panel"></div>
  </div>

  <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
  <script type="module" src="app.js"></script>

</body>
</html>
```

- [ ] **Step 5: Create style.css (complete — all panel styles included now)**

```css
/* ============================================================
   11 Young Street — Stylesheet
   ============================================================ */

/* ----- Reset ----- */
*, *::before, *::after {
  box-sizing: border-box;
  margin: 0;
  padding: 0;
}

/* ----- Base ----- */
body {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', system-ui, sans-serif;
  height: 100dvh;
  overflow: hidden;
}

/* ----- Map ----- */
#map {
  position: fixed;
  inset: 0;
  z-index: 0;
}

/* ----- Theme variables ----- */
:root {
  --accent:     #34d399;
  --accent-bg:  rgba(52, 211, 153, 0.15);
  --radius:     12px;
  --blur:       blur(14px);
  --duration:   0.25s;
}

[data-theme="dark"] {
  --bg-panel:   rgba(8, 18, 28, 0.72);
  --text:       #edf2f7;
  --text-muted: rgba(237, 242, 247, 0.52);
  --border:     rgba(52, 211, 153, 0.28);
  --shadow:     0 4px 28px rgba(0, 0, 0, 0.5);
}

[data-theme="light"] {
  --bg-panel:   rgba(255, 255, 255, 0.82);
  --text:       #1a2530;
  --text-muted: rgba(26, 37, 48, 0.55);
  --border:     rgba(52, 211, 153, 0.38);
  --shadow:     0 4px 28px rgba(0, 0, 0, 0.12);
}

/* ----- Panel base ----- */
.panel {
  background: var(--bg-panel);
  backdrop-filter: var(--blur);
  -webkit-backdrop-filter: var(--blur);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  box-shadow: var(--shadow);
  color: var(--text);
  padding: 12px 16px;
  transition:
    background var(--duration) ease,
    border-color var(--duration) ease,
    box-shadow var(--duration) ease;
}

/* ----- Top bar ----- */
.top-bar {
  position: fixed;
  top: 14px;
  left: 14px;
  right: 14px;
  z-index: 1000;
  display: flex;
  align-items: flex-start;
  gap: 10px;
  pointer-events: none;
}

.top-bar > * { pointer-events: auto; }

.property-title {
  flex: 1;
  text-align: center;
  font-size: 12px;
  font-weight: 500;
  letter-spacing: 0.04em;
  color: #fff;
  text-shadow: 0 1px 8px rgba(0, 0, 0, 0.9);
  padding-top: 6px;
  pointer-events: none;
}

.top-right {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 8px;
}

/* ----- Bottom left ----- */
.bottom-left {
  position: fixed;
  bottom: 34px;
  left: 14px;
  z-index: 1000;
  display: flex;
  flex-direction: column;
  gap: 10px;
  max-width: 300px;
}

/* ----- Theme toggle ----- */
.theme-btn {
  background: var(--bg-panel);
  backdrop-filter: var(--blur);
  -webkit-backdrop-filter: var(--blur);
  border: 1px solid var(--border);
  border-radius: 8px;
  box-shadow: var(--shadow);
  color: var(--text);
  cursor: pointer;
  font-size: 15px;
  line-height: 1;
  padding: 6px 10px;
  transition: background var(--duration) ease, border-color var(--duration) ease;
}

.theme-btn:hover { filter: brightness(1.15); }

/* ----- Clock panel ----- */
#panel-clock { min-width: 170px; }

.clock-time {
  font-size: 26px;
  font-weight: 700;
  letter-spacing: -0.5px;
  line-height: 1;
}

.clock-date {
  font-size: 11px;
  color: var(--text-muted);
  margin-top: 4px;
}

.clock-sun {
  display: flex;
  gap: 14px;
  margin-top: 8px;
  font-size: 11px;
  color: var(--accent);
}

/* ----- Weather panel ----- */
#panel-weather { min-width: 210px; }

.weather-current {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
  line-height: 1;
}

.weather-icon   { font-size: 22px; }
.weather-temp   { font-size: 20px; font-weight: 700; }
.weather-label  { font-size: 11px; color: var(--text-muted); }
.weather-wind   { font-size: 11px; color: var(--text-muted); margin-left: auto; }

.weather-forecast {
  display: flex;
  gap: 8px;
  margin-top: 10px;
  padding-top: 10px;
  border-top: 1px solid var(--border);
}

.forecast-day      { flex: 1; text-align: center; font-size: 10px; }
.forecast-date     { color: var(--text-muted); margin-bottom: 3px; }
.forecast-icon     { font-size: 16px; margin-bottom: 2px; }
.forecast-temps    { font-weight: 600; }

.weather-unavailable,
.weather-loading   { font-size: 12px; color: var(--text-muted); }

/* ----- Tides panel ----- */
.tides-header {
  font-size: 10px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: var(--accent);
  margin-bottom: 4px;
}

.tides-note {
  font-size: 10px;
  color: var(--text-muted);
  font-style: italic;
  margin-bottom: 8px;
}

.tides-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 11px;
}

.tides-table th {
  color: var(--text-muted);
  font-weight: 500;
  text-align: left;
  padding-bottom: 4px;
}

.tides-table td { padding: 2px 6px 2px 0; }

.tide-H { color: var(--accent); font-weight: 700; }
.tide-L { color: var(--text-muted); }

/* ----- Property panel ----- */
#panel-property { max-width: 300px; }

.tabs {
  display: flex;
  gap: 2px;
  margin-bottom: 8px;
  border-bottom: 1px solid var(--border);
  padding-bottom: 6px;
}

.tab {
  background: none;
  border: none;
  border-radius: 6px;
  color: var(--text-muted);
  cursor: pointer;
  font-size: 11px;
  font-weight: 600;
  padding: 3px 10px;
  transition: background var(--duration) ease, color var(--duration) ease;
}

.tab:hover { color: var(--text); }

.tab.active {
  background: var(--accent-bg);
  color: var(--accent);
}

.tab-content             { font-size: 11px; }
.tab-content.hidden      { display: none; }

/* Overview */
.overview-row {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  padding: 4px 0;
  border-bottom: 1px solid rgba(52, 211, 153, 0.08);
  gap: 8px;
}

.overview-label { color: var(--text-muted); flex-shrink: 0; }
.overview-value { color: var(--text); font-weight: 500; text-align: right; }

/* Contacts */
.contacts-filter {
  width: 100%;
  background: transparent;
  border: 1px solid var(--border);
  border-radius: 6px;
  color: var(--text);
  font-size: 11px;
  outline: none;
  padding: 5px 8px;
  margin-bottom: 8px;
  transition: border-color var(--duration) ease;
}

.contacts-filter:focus       { border-color: var(--accent); }
.contacts-filter::placeholder { color: var(--text-muted); }

.contacts-list {
  max-height: 180px;
  overflow-y: auto;
}

.contact-row {
  padding: 5px 0;
  border-bottom: 1px solid rgba(52, 211, 153, 0.06);
}

.contact-trade   { font-weight: 700; font-size: 11px; }
.contact-company { color: var(--text-muted); font-size: 10px; }
.contact-person  { font-size: 10px; margin-top: 2px; }

.contact-links   { display: flex; gap: 10px; margin-top: 2px; }
.contact-links a { color: var(--accent); font-size: 10px; text-decoration: none; }
.contact-links a:hover { text-decoration: underline; }

.contacts-empty { color: var(--text-muted); font-style: italic; padding: 8px 0; }

/* Documents */
.docs-note { color: var(--text-muted); font-style: italic; line-height: 1.5; }

/* ----- Responsive (≤ 640 px) ----- */
@media (max-width: 640px) {
  body { overflow-y: auto; height: auto; }

  #map {
    position: relative;
    height: 50vh;
  }

  .top-bar {
    position: relative;
    top: auto; left: auto; right: auto;
    flex-direction: column;
    padding: 12px;
    gap: 10px;
  }

  .top-right {
    flex-direction: row;
    flex-wrap: wrap;
    align-items: flex-start;
  }

  .property-title {
    text-align: left;
    color: var(--text);
    text-shadow: none;
  }

  .bottom-left {
    position: relative;
    bottom: auto; left: auto;
    max-width: 100%;
    padding: 12px;
  }

  #panel-property { max-width: 100%; }
  #panel-weather  { min-width: unset; }
}
```

- [ ] **Step 6: Create stub app.js**

```javascript
// Entry point — bootstraps map and all panels.
// Each import line is added as its module is built (Tasks 2–7).
```

- [ ] **Step 7: Create stub JS files (so future imports don't error)**

Each file exports its init function as an empty stub:

`js/map.js`:
```javascript
export function initMap() {}
```

`js/theme.js`:
```javascript
export function initTheme() {}
```

`js/panels/clock.js`:
```javascript
export function initClock() { return {}; }
```

`js/panels/weather.js`:
```javascript
export async function initWeather() {}
```

`js/panels/tides.js`:
```javascript
export function initTides() {}
```

`js/panels/property.js`:
```javascript
export async function initProperty() {}
```

- [ ] **Step 8: Verify skeleton**

Start server:
```bash
cd young-street-dashboard && python3 -m http.server 8080
```
Open `http://localhost:8080`.

Expected: white/dark page with no errors in the browser console. The page should load and show nothing visible yet (map container is empty). Check DevTools → Console: no errors.

- [ ] **Step 9: Commit**

```bash
git add young-street-dashboard/
git commit -m "feat: scaffold property dashboard project"
```

---

## Task 2: Map

**Files:**
- Replace: `js/map.js`
- Replace: `app.js`

- [ ] **Step 1: Write js/map.js**

```javascript
const LAT = -36.47509646412374;
const LNG = 174.73539799623094;

export function initMap() {
  const map = L.map('map').setView([LAT, LNG], 16);

  const layers = {
    standard: L.tileLayer(
      'https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',
      {
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
        maxZoom: 19,
      }
    ),
    satellite: L.tileLayer(
      'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
      {
        attribution: 'Tiles &copy; Esri &mdash; Source: Esri, i-cubed, USDA, USGS, AEX, GeoEye, Getmapping, Aerogrid, IGN, IGP, UPR-EGP, and the GIS User Community',
        maxZoom: 19,
      }
    ),
    topo: L.tileLayer(
      'https://{s}.tile.opentopomap.org/{z}/{x}/{y}.png',
      {
        attribution: 'Map data: &copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors, <a href="http://viewfinderpanoramas.org">SRTM</a> | Map style: &copy; <a href="https://opentopomap.org">OpenTopoMap</a>',
        maxZoom: 17,
      }
    ),
  };

  // Satellite is the dark-theme default
  layers.satellite.addTo(map);

  L.control.layers({
    'Standard':    layers.standard,
    'Satellite':   layers.satellite,
    'Topographic': layers.topo,
  }).addTo(map);

  L.marker([LAT, LNG])
    .addTo(map)
    .bindPopup('<strong>11 Young Street</strong><br>Scotts Landing, Mahurangi East');

  return { map, layers };
}
```

- [ ] **Step 2: Update app.js**

```javascript
import { initMap } from './js/map.js';

const { map, layers } = initMap();
```

- [ ] **Step 3: Verify map**

Reload `http://localhost:8080`.

Expected:
- Full-screen satellite map centred on Scotts Landing
- A marker visible on the property — click it to see the popup "11 Young Street / Scotts Landing, Mahurangi East"
- Layer control (top-right, Leaflet native) — switch to Standard and Topographic; each should load without error
- Attribution text visible at bottom-right for the active layer

- [ ] **Step 4: Commit**

```bash
git add young-street-dashboard/js/map.js young-street-dashboard/app.js
git commit -m "feat: add Leaflet map with three layers and property marker"
```

---

## Task 3: Theme System

**Files:**
- Replace: `js/theme.js`
- Replace: `app.js`

- [ ] **Step 1: Write js/theme.js**

```javascript
export function initTheme(map, layers) {
  const html  = document.documentElement;
  const btn   = document.getElementById('theme-toggle');
  let userPickedLayer = false;

  // Detect when user manually switches base layer via the Leaflet control
  map.on('baselayerchange', () => { userPickedLayer = true; });

  function applyTheme(theme) {
    html.setAttribute('data-theme', theme);
    btn.textContent = theme === 'dark' ? '☀️' : '🌙';

    if (!userPickedLayer) {
      const target = theme === 'dark' ? layers.satellite : layers.standard;
      // Remove whichever base layer is currently active
      [layers.standard, layers.satellite, layers.topo].forEach(l => {
        if (map.hasLayer(l)) map.removeLayer(l);
      });
      target.addTo(map);
    }

    // After a theme switch, reset so the NEXT switch can auto-pick again
    userPickedLayer = false;
  }

  btn.addEventListener('click', () => {
    const current = html.getAttribute('data-theme');
    applyTheme(current === 'dark' ? 'light' : 'dark');
  });

  // Dark is already set in HTML; no further init needed
}
```

- [ ] **Step 2: Update app.js**

```javascript
import { initMap }   from './js/map.js';
import { initTheme } from './js/theme.js';

const { map, layers } = initMap();
initTheme(map, layers);
```

- [ ] **Step 3: Verify theme toggle**

Reload `http://localhost:8080`.

Expected:
- Page loads in dark mode (dark translucent header area, satellite map)
- Click ☀️ button → switches to light mode: lighter panel backgrounds, Standard map layer loads automatically
- Click 🌙 button → switches back to dark mode: Satellite layer loads automatically
- Manually switch to Topographic via layer control, then click the theme toggle → map stays on Topographic (user preference respected)
- After that theme switch, click the toggle again → map auto-switches to the theme default (Satellite for dark, Standard for light)
- Smooth transition on panel backgrounds when toggling

- [ ] **Step 4: Commit**

```bash
git add young-street-dashboard/js/theme.js young-street-dashboard/app.js
git commit -m "feat: add dark/light theme toggle with auto map layer switching"
```

---

## Task 4: Clock Panel

**Files:**
- Replace: `js/panels/clock.js`
- Replace: `app.js`

- [ ] **Step 1: Write js/panels/clock.js**

```javascript
export function initClock() {
  const container = document.getElementById('panel-clock');

  container.innerHTML = `
    <div class="clock-time" id="clock-time">--:-- --</div>
    <div class="clock-date" id="clock-date">—</div>
    <div class="clock-sun"  id="clock-sun">
      <span>🌅 --:--</span>
      <span>🌇 --:--</span>
    </div>
  `;

  function tick() {
    const now = new Date();

    document.getElementById('clock-time').textContent =
      now.toLocaleTimeString('en-NZ', {
        timeZone: 'Pacific/Auckland',
        hour:     '2-digit',
        minute:   '2-digit',
        second:   '2-digit',
        hour12:   true,
      });

    document.getElementById('clock-date').textContent =
      now.toLocaleDateString('en-NZ', {
        timeZone: 'Pacific/Auckland',
        weekday:  'long',
        day:      'numeric',
        month:    'long',
        year:     'numeric',
      });
  }

  tick();
  setInterval(tick, 1000);

  // Called by weather.js once it has fetched today's sunrise/sunset ISO strings
  function setSunTimes(sunriseISO, sunsetISO) {
    const fmt = iso =>
      new Date(iso).toLocaleTimeString('en-NZ', {
        timeZone: 'Pacific/Auckland',
        hour:     '2-digit',
        minute:   '2-digit',
        hour12:   true,
      });

    document.getElementById('clock-sun').innerHTML = `
      <span>🌅 ${fmt(sunriseISO)}</span>
      <span>🌇 ${fmt(sunsetISO)}</span>
    `;
  }

  return { setSunTimes };
}
```

- [ ] **Step 2: Update app.js**

```javascript
import { initMap }   from './js/map.js';
import { initTheme } from './js/theme.js';
import { initClock } from './js/panels/clock.js';

const { map, layers } = initMap();
initTheme(map, layers);
const clock = initClock();
```

- [ ] **Step 3: Verify clock**

Reload `http://localhost:8080`.

Expected:
- Top-left panel visible with a frosted-glass appearance
- Shows the current time in `HH:MM:SS AM/PM` format, updating every second
- Shows today's date (e.g. "Monday, 18 May 2026") in Auckland timezone — not your machine's local time if you're in a different timezone
- Sunrise/sunset shows `🌅 --:--` and `🌇 --:--` placeholders (will be filled by Task 5)
- Both dark and light themes show the clock panel correctly

- [ ] **Step 4: Commit**

```bash
git add young-street-dashboard/js/panels/clock.js young-street-dashboard/app.js
git commit -m "feat: add live Auckland clock panel with sunrise/sunset placeholders"
```

---

## Task 5: Weather Panel

**Files:**
- Replace: `js/panels/weather.js`
- Replace: `app.js`

- [ ] **Step 1: Write js/panels/weather.js**

```javascript
const API_URL =
  'https://api.open-meteo.com/v1/forecast' +
  '?latitude=-36.4751&longitude=174.7354' +
  '&current=temperature_2m,weather_code,wind_speed_10m' +
  '&daily=weather_code,temperature_2m_max,temperature_2m_min,sunrise,sunset' +
  '&timezone=Pacific%2FAuckland';

// WMO weather interpretation codes → label + emoji icon
const WMO = {
  0:  { label: 'Clear sky',       icon: '☀️'  },
  1:  { label: 'Mainly clear',    icon: '🌤️'  },
  2:  { label: 'Partly cloudy',   icon: '⛅'  },
  3:  { label: 'Overcast',        icon: '☁️'  },
  45: { label: 'Foggy',           icon: '🌫️' },
  48: { label: 'Icy fog',         icon: '🌫️' },
  51: { label: 'Light drizzle',   icon: '🌦️'  },
  53: { label: 'Drizzle',         icon: '🌦️'  },
  55: { label: 'Heavy drizzle',   icon: '🌦️'  },
  61: { label: 'Light rain',      icon: '🌧️'  },
  63: { label: 'Rain',            icon: '🌧️'  },
  65: { label: 'Heavy rain',      icon: '🌧️'  },
  71: { label: 'Light snow',      icon: '❄️'  },
  73: { label: 'Snow',            icon: '❄️'  },
  75: { label: 'Heavy snow',      icon: '❄️'  },
  80: { label: 'Light showers',   icon: '🌦️'  },
  81: { label: 'Showers',         icon: '🌦️'  },
  82: { label: 'Heavy showers',   icon: '🌦️'  },
  95: { label: 'Thunderstorm',    icon: '⛈️'  },
  96: { label: 'Thunderstorm',    icon: '⛈️'  },
  99: { label: 'Thunderstorm',    icon: '⛈️'  },
};

function wmo(code) {
  return WMO[code] ?? { label: 'Unknown', icon: '🌡️' };
}

function fmtForecastDate(dateStr) {
  // dateStr is "YYYY-MM-DD" in Auckland timezone from the API.
  // Use noon to avoid any date-boundary issues when parsing.
  return new Date(dateStr + 'T12:00:00').toLocaleDateString('en-NZ', {
    timeZone: 'Pacific/Auckland',
    weekday:  'short',
    day:      'numeric',
    month:    'short',
  });
}

export async function initWeather(clock) {
  const container = document.getElementById('panel-weather');
  container.innerHTML = '<div class="weather-loading">Loading weather…</div>';

  try {
    const res = await fetch(API_URL);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();

    const cur   = data.current;
    const daily = data.daily;
    const cond  = wmo(cur.weather_code);

    // Share today's sunrise/sunset with the clock panel (index 0 = today)
    clock.setSunTimes(daily.sunrise[0], daily.sunset[0]);

    // Next 3 days = indices 1, 2, 3
    const forecastHTML = [1, 2, 3].map(i => `
      <div class="forecast-day">
        <div class="forecast-date">${fmtForecastDate(daily.time[i])}</div>
        <div class="forecast-icon">${wmo(daily.weather_code[i]).icon}</div>
        <div class="forecast-temps">
          ${Math.round(daily.temperature_2m_max[i])}° /
          ${Math.round(daily.temperature_2m_min[i])}°
        </div>
      </div>
    `).join('');

    container.innerHTML = `
      <div class="weather-current">
        <span class="weather-icon">${cond.icon}</span>
        <span class="weather-temp">${Math.round(cur.temperature_2m)}°C</span>
        <span class="weather-label">${cond.label}</span>
        <span class="weather-wind">💨 ${Math.round(cur.wind_speed_10m)} km/h</span>
      </div>
      <div class="weather-forecast">${forecastHTML}</div>
    `;
  } catch {
    container.innerHTML = '<div class="weather-unavailable">⚠ Weather unavailable</div>';
  }
}
```

- [ ] **Step 2: Update app.js**

```javascript
import { initMap }     from './js/map.js';
import { initTheme }   from './js/theme.js';
import { initClock }   from './js/panels/clock.js';
import { initWeather } from './js/panels/weather.js';

const { map, layers } = initMap();
initTheme(map, layers);
const clock = initClock();
initWeather(clock);
```

- [ ] **Step 3: Verify weather**

Reload `http://localhost:8080`.

Expected:
- Top-right panel shows current temperature (°C), a weather icon, condition label, wind speed
- Three forecast days appear below a divider, each with a short date, icon, and high/low temps
- Clock panel's sunrise/sunset times are now filled in (no longer `--:--`)
- To test the error state: open DevTools → Network → throttle to "Offline", reload. The weather panel should show "⚠ Weather unavailable" — not a blank panel or JS error.

- [ ] **Step 4: Commit**

```bash
git add young-street-dashboard/js/panels/weather.js young-street-dashboard/app.js
git commit -m "feat: add weather panel with Open-Meteo forecast and sunrise/sunset"
```

---

## Task 6: Property Panel

**Files:**
- Replace: `js/panels/property.js`
- Replace: `app.js`

- [ ] **Step 1: Write js/panels/property.js**

```javascript
export async function initProperty() {
  const container = document.getElementById('panel-property');

  // Load contact data
  let contacts = [];
  try {
    const res = await fetch('contacts.json');
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    contacts = (await res.json()).contacts;
  } catch {
    // Contacts tab will show the empty state
  }

  container.innerHTML = `
    <div class="tabs">
      <button class="tab active" data-tab="overview">Overview</button>
      <button class="tab"        data-tab="contacts">Contacts</button>
      <button class="tab"        data-tab="documents">Documents</button>
    </div>
    <div class="tab-content"        id="tab-overview">${renderOverview()}</div>
    <div class="tab-content hidden" id="tab-contacts">${renderContacts(contacts)}</div>
    <div class="tab-content hidden" id="tab-documents">${renderDocuments()}</div>
  `;

  // Tab switching
  container.querySelectorAll('.tab').forEach(btn => {
    btn.addEventListener('click', () => {
      container.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
      container.querySelectorAll('.tab-content').forEach(c => c.classList.add('hidden'));
      btn.classList.add('active');
      document.getElementById('tab-' + btn.dataset.tab).classList.remove('hidden');
    });
  });

  // Contacts filter
  const filterInput = container.querySelector('.contacts-filter');
  const contactsList = container.querySelector('.contacts-list');
  if (filterInput) {
    filterInput.addEventListener('input', () => {
      contactsList.innerHTML = buildContactRows(
        contacts,
        filterInput.value.trim()
      );
    });
  }
}

function renderOverview() {
  const fields = [
    ['Address',    '11 Young Street, Scotts Landing, Mahurangi East'],
    ['Builder',    'David Reid Homes (DRH)'],
    ['Build year', '—'],
    ['Section',    '—'],
    ['Floor area', '—'],
    ['Rates ref',  '—'],
  ];
  return fields.map(([label, value]) => `
    <div class="overview-row">
      <span class="overview-label">${label}</span>
      <span class="overview-value">${value}</span>
    </div>
  `).join('');
}

function renderContacts(contacts) {
  return `
    <input class="contacts-filter" type="text" placeholder="Search contacts…" />
    <div class="contacts-list">
      ${buildContactRows(contacts, '')}
    </div>
  `;
}

function buildContactRows(contacts, query) {
  const q = query.toLowerCase();
  const filtered = q
    ? contacts.filter(c =>
        c.trade.toLowerCase().includes(q) ||
        c.company.toLowerCase().includes(q) ||
        (c.contact && c.contact.toLowerCase().includes(q))
      )
    : contacts;

  if (filtered.length === 0) {
    return '<div class="contacts-empty">No matches found.</div>';
  }

  return filtered.map(c => {
    const phone = c.phone
      ? `<a href="tel:${c.phone.replace(/\s/g, '')}">${c.phone}</a>`
      : '';

    // If the email field is a URL, skip it (per spec) — just show nothing
    const email = c.email && !c.email.startsWith('http')
      ? `<a href="mailto:${c.email}">${c.email}</a>`
      : '';

    return `
      <div class="contact-row">
        <div class="contact-trade">${c.trade}</div>
        ${c.company  ? `<div class="contact-company">${c.company}</div>` : ''}
        ${c.contact  ? `<div class="contact-person">${c.contact}</div>` : ''}
        <div class="contact-links">${phone}${email}</div>
      </div>
    `;
  }).join('');
}

function renderDocuments() {
  return `
    <p class="docs-note">
      This tab is reserved for future use — warranty documents,
      council links, and other property records.
    </p>
  `;
}
```

- [ ] **Step 2: Update app.js**

```javascript
import { initMap }      from './js/map.js';
import { initTheme }    from './js/theme.js';
import { initClock }    from './js/panels/clock.js';
import { initWeather }  from './js/panels/weather.js';
import { initProperty } from './js/panels/property.js';

const { map, layers } = initMap();
initTheme(map, layers);
const clock = initClock();
initWeather(clock);
initProperty();
```

- [ ] **Step 3: Verify property panel**

Reload `http://localhost:8080`.

Expected:
- Bottom-left shows a property panel with three tabs: Overview, Contacts, Documents
- Overview tab: shows address and builder; the four placeholder fields show `—`
- Contacts tab: all 27 suppliers appear in a scrollable list. Each has a clickable phone number (tel: link). Email addresses appear as mailto: links. Fisher & Paykel and Windsor Hardware entries have no email link (their email fields are URLs — check these two are handled correctly).
- Contacts filter: type "plumb" — only Windybank Plumbing & Drainage rows remain. Clear input — all contacts return.
- Documents tab: shows the placeholder note.
- Switching tabs: clicking each tab shows the right content, no visual glitches.

- [ ] **Step 4: Commit**

```bash
git add young-street-dashboard/js/panels/property.js young-street-dashboard/app.js
git commit -m "feat: add property panel with overview, contacts filter, and documents tab"
```

---

## Task 7: Tides Panel

**Files:**
- Replace: `js/panels/tides.js`
- Replace: `app.js`

- [ ] **Step 1: Write js/panels/tides.js**

The data is separated from the rendering so a real source can be swapped in later without rewriting the display logic.

```javascript
// Static approximate tides for Mahurangi Harbour.
// Sourced from LINZ tide tables — approximate only.
// Replace TIDE_DATA with a real API call when a NIWA key is available.
const TIDE_DATA = [
  { type: 'H', time: '03:48', height: '2.8 m' },
  { type: 'L', time: '10:02', height: '0.3 m' },
  { type: 'H', time: '16:09', height: '2.7 m' },
  { type: 'L', time: '22:24', height: '0.4 m' },
];

function renderTides(tides) {
  const rows = tides.map(t => `
    <tr>
      <td class="tide-${t.type}">${t.type === 'H' ? 'High' : 'Low'}</td>
      <td>${t.time}</td>
      <td>${t.height}</td>
    </tr>
  `).join('');

  return `
    <div class="tides-header">Tides — Mahurangi</div>
    <div class="tides-note">Approximate reference · Live NIWA tides planned</div>
    <table class="tides-table">
      <thead>
        <tr>
          <th>Type</th>
          <th>Time</th>
          <th>Height</th>
        </tr>
      </thead>
      <tbody>${rows}</tbody>
    </table>
  `;
}

export function initTides() {
  const container = document.getElementById('panel-tides');
  container.innerHTML = renderTides(TIDE_DATA);
}
```

- [ ] **Step 2: Update app.js (final version)**

```javascript
import { initMap }      from './js/map.js';
import { initTheme }    from './js/theme.js';
import { initClock }    from './js/panels/clock.js';
import { initWeather }  from './js/panels/weather.js';
import { initProperty } from './js/panels/property.js';
import { initTides }    from './js/panels/tides.js';

const { map, layers } = initMap();
initTheme(map, layers);
const clock = initClock();
initWeather(clock);
initProperty();
initTides();
```

- [ ] **Step 3: Verify tides**

Reload `http://localhost:8080`.

Expected:
- Bottom-left now shows two panels: Tides (above) and Property (below)
- Tides panel shows: "Tides — Mahurangi" header in accent green, italic note "Approximate reference · Live NIWA tides planned", and a 4-row table of High/Low times
- High rows appear in emerald green, Low rows in muted text
- Both themes display the tides panel correctly

- [ ] **Step 4: Commit**

```bash
git add young-street-dashboard/js/panels/tides.js young-street-dashboard/app.js
git commit -m "feat: add static tides panel clearly labelled as approximate"
```

---

## Task 8: Polish Pass

**Files:**
- Modify: `style.css` (responsive tweaks if any issues found)
- Modify: any panel file with visual issues

This task is a browser walkthrough — verify every acceptance criterion, fix any issues found.

- [ ] **Step 1: Full desktop check**

Open `http://localhost:8080` at full browser width. Check each item:

- Map loads with satellite layer and property marker. Popup opens on click.
- Layer control (bottom-right) — switch all three layers; each loads with correct attribution.
- Dark/light toggle — smooth transition, map layer follows, panel backgrounds update.
- Clock — correct Auckland time, ticking, date correct, sunrise/sunset filled after weather loads.
- Weather — current conditions and 3-day forecast visible. No console errors.
- Property panel — all tabs work, Contacts filter works, 27 contacts load.
- Tides — static table visible, "Approximate reference" note present.
- Panels do not cover the map marker at the centre of the screen.
- No JS errors in browser DevTools console.

- [ ] **Step 2: Offline / error state check**

In DevTools → Network → set throttle to "Offline". Reload.

Expected: Weather panel shows "⚠ Weather unavailable". Clock still ticks. Sunrise/sunset stays as `--:--`. No broken panels or blank areas.

Restore network to "No throttling".

- [ ] **Step 3: Mobile check**

Open DevTools → Toggle device toolbar (⌘+Shift+M). Set to iPhone SE (375 × 667) or similar.

Expected:
- Map appears at roughly 50% of viewport height
- Panels stack vertically below the map — readable and usable without panels overlapping each other
- Property panel expands to full width
- No horizontal scrollbar
- All panels remain legible — text is not truncated or clipped

- [ ] **Step 4: Fix any issues found**

Fix layout or style issues discovered in Steps 1–3. Common ones to watch for:
- Weather panel overlapping clock panel on medium screens
- Property panel too wide on desktop (check `max-width: 300px` is applied)
- Theme toggle button text not updating correctly (should show ☀️ when dark, 🌙 when light)

- [ ] **Step 5: Final commit**

```bash
git add young-street-dashboard/
git commit -m "polish: responsive layout, error states, final visual pass"
```

---

## Acceptance Criteria Checklist

Run through these before considering v1 complete:

- [ ] `index.html` opens in browser with no build step (Safari), or via `python3 -m http.server 8080` (Chrome)
- [ ] Map shows 11 Young Street with a marker and working popup
- [ ] All three map layers switch via layer control; each shows correct attribution
- [ ] Dark/light toggle works; default map layer follows theme; user-picked layer is respected
- [ ] Clock shows live Auckland time, date, sunrise, sunset
- [ ] Weather shows current conditions + 3-day forecast; degrades gracefully when offline
- [ ] Tides shows clearly-labelled static placeholder table
- [ ] Property panel has Overview / Contacts / Documents tabs
- [ ] Contacts tab loads all 27 suppliers from contacts.json with working filter
- [ ] Fisher & Paykel and Windsor Hardware: no broken mailto link (email field is a URL — correctly skipped)
- [ ] Panels are frosted-glass; layout reads as a modern dashboard
- [ ] Layout is usable on 375px phone width
- [ ] No JS errors in browser console
