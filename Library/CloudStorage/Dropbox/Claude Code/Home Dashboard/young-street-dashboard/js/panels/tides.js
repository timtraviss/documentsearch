const CSV_PATH = 'tides_31days_from_19May.csv';
const TZ = 'Pacific/Auckland';

const SVG_W   = 240;
const SVG_CH  = 56;   // chart area height
const PAD_X   = 6;
const PAD_Y   = 5;
const LABEL_H = 12;
const SVG_H   = SVG_CH + LABEL_H;

// --- Parsing ---

function parseCsv(text) {
  const lines = text.split('\n');
  const start = lines.findIndex(l => l.trim().startsWith('TIME,VALUE'));
  if (start === -1) return [];
  return lines.slice(start + 1)
    .map(l => l.trim()).filter(Boolean)
    .map(l => {
      const [rawT, rawV] = l.split(',');
      const t = new Date(rawT.replace(/"/g, ''));
      const v = parseFloat(rawV);
      return isNaN(v) || isNaN(t.getTime()) ? null : { time: t, value: v };
    }).filter(Boolean);
}

// Classify H/L by comparing each turning point to its neighbours
function classifyHL(entries) {
  return entries.map((e, i) => {
    const prev = entries[i - 1]?.value ?? e.value;
    const next = entries[i + 1]?.value ?? e.value;
    return { ...e, type: e.value >= prev && e.value >= next ? 'H' : 'L' };
  });
}

// --- Time utils ---

function nzDateKey(date) {
  return date.toLocaleDateString('en-CA', { timeZone: TZ });
}

function fmtTime(date) {
  return date.toLocaleTimeString('en-NZ', {
    timeZone: TZ, hour: '2-digit', minute: '2-digit', hour12: false,
  });
}

// Returns UTC Date objects for Auckland midnight today and +24h
function nzDayBounds(now) {
  const p = {};
  new Intl.DateTimeFormat('en-US', {
    timeZone: TZ,
    hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false,
  }).formatToParts(now).forEach(({ type, value }) => { p[type] = parseInt(value) || 0; });
  const elapsed = (p.hour * 3600 + p.minute * 60 + p.second) * 1000;
  const start = new Date(now.getTime() - elapsed);
  return { start, end: new Date(start.getTime() + 86400000) };
}

// --- Interpolation ---

function cosineInterp(t1, h1, t2, h2, t) {
  const mu = (1 - Math.cos((t - t1) / (t2 - t1) * Math.PI)) / 2;
  return h1 + (h2 - h1) * mu;
}

function heightAt(entries, tMs) {
  let before = null, after = null;
  for (const e of entries) {
    if (e.time.getTime() <= tMs) before = e;
    else if (!after) after = e;
  }
  if (!before) return after.value;
  if (!after)  return before.value;
  return cosineInterp(before.time.getTime(), before.value, after.time.getTime(), after.value, tMs);
}

// --- SVG chart ---

function renderSVG(allEntries, todayEntries, now) {
  const { start, end } = nzDayBounds(now);
  const step = 10 * 60 * 1000;

  const pts = [];
  for (let t = start.getTime(); t <= end.getTime(); t += step) {
    pts.push({ t, h: heightAt(allEntries, t) });
  }

  const hs     = pts.map(p => p.h);
  const minH   = Math.min(...hs);
  const maxH   = Math.max(...hs);
  const hRange = maxH - minH || 1;

  const toX = t => PAD_X + (t - start.getTime()) / (end.getTime() - start.getTime()) * (SVG_W - 2 * PAD_X);
  const toY = h => PAD_Y + (1 - (h - minH) / hRange) * (SVG_CH - 2 * PAD_Y);

  const pathD  = pts.map((p, i) => `${i ? 'L' : 'M'}${toX(p.t).toFixed(1)},${toY(p.h).toFixed(1)}`).join(' ');
  const bottom = SVG_CH - PAD_Y;
  const fillD  = `${pathD} L${toX(pts.at(-1).t).toFixed(1)},${bottom} L${toX(pts[0].t).toFixed(1)},${bottom} Z`;

  const nowX = toX(now.getTime()).toFixed(1);
  const nowY = toY(heightAt(allEntries, now.getTime())).toFixed(1);

  const dots = todayEntries.map(e => {
    const cx   = toX(e.time.getTime()).toFixed(1);
    const cy   = toY(e.value).toFixed(1);
    const fill = e.type === 'H' ? '#34d399' : 'rgba(237,242,247,0.35)';
    return `<circle cx="${cx}" cy="${cy}" r="2.5" fill="${fill}"/>`;
  }).join('');

  const labels = [6, 12, 18].map(h => {
    const x     = toX(start.getTime() + h * 3600000).toFixed(1);
    const label = h === 12 ? '12pm' : `${h > 12 ? h - 12 : h}${h >= 12 ? 'pm' : 'am'}`;
    return `<text x="${x}" y="${SVG_CH + 2}" font-size="7" text-anchor="middle" fill="rgba(237,242,247,0.28)" dominant-baseline="hanging">${label}</text>`;
  }).join('');

  return `<svg class="tide-svg" viewBox="0 0 ${SVG_W} ${SVG_H}" width="100%" xmlns="http://www.w3.org/2000/svg">
    <defs>
      <linearGradient id="tideFill" x1="0" y1="0" x2="0" y2="1">
        <stop offset="0%"   stop-color="#34d399" stop-opacity="0.18"/>
        <stop offset="100%" stop-color="#34d399" stop-opacity="0.02"/>
      </linearGradient>
    </defs>
    <path d="${fillD}" fill="url(#tideFill)"/>
    <path d="${pathD}" fill="none" stroke="#34d399" stroke-width="1.5" stroke-linejoin="round"/>
    <line x1="${nowX}" y1="${PAD_Y}" x2="${nowX}" y2="${bottom}"
          stroke="rgba(237,242,247,0.35)" stroke-width="1" stroke-dasharray="2,2"/>
    <circle cx="${nowX}" cy="${nowY}" r="2.8" fill="white" stroke="#34d399" stroke-width="1.5"/>
    ${dots}
    ${labels}
  </svg>`;
}

// --- Countdown ---

function fmtCountdown(ms) {
  const totalMin = Math.round(ms / 60000);
  const h = Math.floor(totalMin / 60);
  const m = totalMin % 60;
  if (h === 0) return `${m}m`;
  return m === 0 ? `${h}h` : `${h}h ${m}m`;
}

// --- Render ---

function renderTides(allEntries) {
  const now      = new Date();
  const todayKey = nzDateKey(now);

  const todayEntries = allEntries.filter(e => nzDateKey(e.time) === todayKey);
  const upcoming     = allEntries.filter(e => e.time > now);

  let tableEntries = todayEntries;
  if (todayEntries.every(e => e.time <= now)) {
    tableEntries = upcoming.slice(0, 4);
  }

  if (tableEntries.length === 0) {
    return `<div class="tides-header">Tides — Mahurangi</div>
            <div class="tides-note">No upcoming data</div>`;
  }

  const next = upcoming[0];

  const callout = next ? `
    <div class="tide-callout">
      <span class="tide-callout-type tide-${next.type}">${next.type === 'H' ? '▲ High' : '▼ Low'}</span>
      <span class="tide-callout-height">${next.value.toFixed(2)} m</span>
      <span class="tide-callout-when">in ${fmtCountdown(next.time - now)}</span>
    </div>` : '';

  const rows = tableEntries.map(t => {
    const past   = t.time < now;
    const isNext = next && t.time.getTime() === next.time.getTime();
    return `<tr class="${past ? 'tide-past' : ''}${isNext ? ' tide-next-row' : ''}">
      <td class="tide-${t.type}">${t.type === 'H' ? 'High' : 'Low'}</td>
      <td>${fmtTime(t.time)}</td>
      <td>${t.value.toFixed(2)} m</td>
    </tr>`;
  }).join('');

  return `
    <div class="tides-header">Tides — Mahurangi</div>
    ${renderSVG(allEntries, todayEntries, now)}
    ${callout}
    <table class="tides-table">
      <thead><tr><th>Type</th><th>Time</th><th>Height</th></tr></thead>
      <tbody>${rows}</tbody>
    </table>`;
}

export async function initTides() {
  const container = document.getElementById('panel-tides');
  try {
    const text = await fetch(CSV_PATH).then(r => {
      if (!r.ok) throw new Error(`HTTP ${r.status}`);
      return r.text();
    });
    container.innerHTML = renderTides(classifyHL(parseCsv(text)));
  } catch (err) {
    console.error('[tides]', err);
    container.innerHTML = '<div class="tides-unavailable">⚠ Tide data unavailable</div>';
  }
}
