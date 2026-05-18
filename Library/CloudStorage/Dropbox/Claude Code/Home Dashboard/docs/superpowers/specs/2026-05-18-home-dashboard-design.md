# Design Spec — 11 Young Street Property Dashboard

**Date:** 2026-05-18
**Status:** Approved
**Author:** Tim Traviss (brainstormed with Claude)

---

## Overview

A single-screen web dashboard for the property at 11 Young Street, Scotts Landing, Mahurangi East. Full-screen interactive Leaflet map as the canvas, with frosted-glass information panels floating on top. Runs locally — open `index.html` in a browser, no build step.

---

## Tech Stack

| Concern | Choice |
|---------|--------|
| Markup/styling | Plain HTML5 + CSS3 |
| Logic | Vanilla JS (ES modules) |
| Mapping | Leaflet.js via CDN (unpkg.com) |
| Build step | None |
| Data | `contacts.json` (local) |
| Weather/sun API | Open-Meteo (free, no key) |

No React, no npm, no bundler. Code on disk is code that runs — directly editable by a non-developer.

---

## Project Location & File Structure

Root: `Dropbox/Claude Code/Home Dashboard/young-street-dashboard/`

```
young-street-dashboard/
├── index.html
├── style.css
├── app.js
├── contacts.json          ← copy of parent folder's contacts.json
├── .env.example           ← placeholder for future NIWA tide key
└── js/
    ├── map.js
    ├── theme.js
    └── panels/
        ├── clock.js
        ├── weather.js
        ├── tides.js
        └── property.js
```

Each panel file is self-contained: owns its DOM rendering and data fetching. `app.js` imports and initialises each one. Adding a future panel = one new file + one import line.

---

## Layout

Full-bleed map as canvas. Panels float on top as frosted-glass cards.

```
┌─────────────────────────────────────────────────────┐
│ [ Clock / Sun ]      11 Young Street     [ Weather ] │
│                                          [ Theme ⏾ ] │
│                                                       │
│                  FULL-SCREEN MAP                      │
│              (marker on the property)                 │
│                                                       │
│ [ Tides ]                            [ Layers ▾ ]    │
│ [ Property ▸ ]                                        │
└─────────────────────────────────────────────────────┘
```

- **Top-left:** Clock / date / sunrise / sunset
- **Top-centre:** Property address title (small, unobtrusive)
- **Top-right:** Weather panel + theme toggle
- **Bottom-left:** Tides panel + Property panel
- **Bottom-right:** Leaflet native layer control

**Mobile:** panels stack in a scrollable column below a shorter map.

---

## Map

- **Library:** Leaflet via CDN
- **Centre:** lat `-36.47509646412374`, lng `174.73539799623094`
- **Default zoom:** 16
- **Marker:** on coordinates, popup "11 Young Street, Scotts Landing"
- **Three switchable base layers:**

| Layer | Source |
|-------|--------|
| Standard | OpenStreetMap |
| Satellite | Esri World Imagery |
| Topographic | Esri World Topo Map |

All free, no API key. Correct attribution included for each (required by tile providers).

Default layer follows theme: Satellite on dark, Standard on light. If user manually switches layer, respect their choice until the next theme toggle.

---

## Panels

All panels: frosted-glass cards — semi-transparent background, `backdrop-filter: blur()`, rounded corners, soft shadow, hairline border in the accent colour.

### Clock / Sun
- Live clock, updates every second, Pacific/Auckland timezone (explicit — never rely on viewer's machine)
- Current date
- Sunrise and sunset from Open-Meteo daily data (shared fetch with Weather panel — one API call)

### Weather
- **API:** Open-Meteo Forecast (free, no key)
- **Endpoint:** `https://api.open-meteo.com/v1/forecast?latitude=-36.4751&longitude=174.7354&current=temperature_2m,weather_code,wind_speed_10m&daily=weather_code,temperature_2m_max,temperature_2m_min,sunrise,sunset&timezone=Pacific/Auckland`
- **Current:** temperature, WMO weather code → label + icon, wind speed
- **Forecast:** next 3 days, high/low + condition icon
- **Sunrise/sunset** daily fields shared with Clock panel (fetch once, pass data)
- On fetch failure: show "weather unavailable" state, never blank/broken

### Tides (v1 — static placeholder)
- No reliable free/keyless tide API for Mahurangi Harbour
- Shows a clearly-labelled static table of representative high/low tide times
- Visible note: "Approximate reference — live NIWA tides planned"
- Rendering is separate from the hardcoded data so a real source can be slotted in without a rewrite
- Future phase: NIWA Tide API (free tier, requires key). Key needs a server-side proxy — cannot be safely exposed in client-side JS

### Property (tabbed)
Three tabs, trivially extensible to a 4th/5th:

1. **Overview** — address, builder (David Reid Homes), plus four placeholder fields displayed as `—`: build year, section size, floor area, council rates reference. Tim fills these in directly in the HTML.
2. **Contacts** — loads `contacts.json` at runtime (27 suppliers). Each row: trade, company, contact, phone (`tel:` link), email (`mailto:` link; if email field contains a URL, skip the link). Search/filter box at top.
3. **Documents / Links** — heading only, note "for future use (warranty docs, council links)".

---

## Theme System

Toggle switches between dark (default) and light. Both use frosted-glass panels.

| Aspect | Dark | Light |
|--------|------|-------|
| Panel background | Dark semi-transparent | Light semi-transparent |
| Text | Light | Dark |
| Default map layer | Satellite | Standard |

- Implemented with CSS custom properties on a root class (`[data-theme="dark"]` / `[data-theme="light"]`)
- `theme.js` swaps the class — no duplicated CSS blocks
- Theme does not persist between visits in v1

---

## Design Direction

- **Accent colour:** Emerald green (`#34d399`) — consistent across both themes, used on panel borders, tab highlights, hover states, interactive elements
- **Typography:** System font stack (no web font load in v1)
- **Panels:** generous border radius, backdrop blur, hairline accent-colour border, soft shadow
- **Transitions:** smooth, subtle on theme switch and panel interactions — nothing flashy
- **Panels must not obscure the map marker** — layout keeps map centre clear

---

## Build Sequence

Build in phases, dashboard runnable after each:

1. **Skeleton** — `index.html`, `style.css`, `app.js`. Page loads, empty.
2. **Map** — `map.js`: three layers, layer control, marker + popup.
3. **Theme** — `theme.js`, CSS variables, toggle. Both themes + default-layer switch.
4. **Clock panel** — `clock.js`. Live Auckland time + date.
5. **Weather panel** — `weather.js`. Open-Meteo fetch, current + 3-day forecast, sunrise/sunset shared.
6. **Property panel** — `property.js`. Tabs; Contacts loads `contacts.json` with filter.
7. **Tides panel** — `tides.js`. Static placeholder, clearly labelled.
8. **Polish** — responsive behaviour, fetch-failure states, attribution, final styling pass.

---

## Acceptance Criteria

- [ ] `index.html` opens in a browser with no build step
- [ ] Map shows 11 Young Street with marker and working popup
- [ ] All three map layers switch via layer control
- [ ] Dark/light toggle works; default map layer follows theme
- [ ] Clock shows live Auckland time, date, sunrise, sunset
- [ ] Weather shows current conditions + 3-day forecast; degrades gracefully on API failure
- [ ] Tides shows clearly-labelled static placeholder
- [ ] Property panel has Overview / Contacts / Documents tabs; Contacts loads all 27 suppliers with working filter
- [ ] Panels are frosted-glass; layout reads as a modern dashboard
- [ ] Layout is usable on phone-width screen
- [ ] Code is plain, commented where useful, organised per file structure above

---

## Future Phases (architecture anticipates, v1 does not build)

- AI chat panel (`js/panels/chat.js` + one import line in `app.js`)
- Live NIWA tides (needs server-side proxy for API key)
- Theme persistence (localStorage)
- Live contacts from source spreadsheet
- Documents tab populated with warranty docs / council links
- Hosting (currently local file)
