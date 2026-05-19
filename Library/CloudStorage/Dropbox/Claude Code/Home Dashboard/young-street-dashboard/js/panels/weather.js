import { OPENWEATHER_KEY } from '../../config.js';

const LAT = -36.4751;
const LNG = 174.7354;
const OW  = 'https://api.openweathermap.org/data/2.5';

function owIcon(id) {
  if (id >= 200 && id < 300) return '⛈️';
  if (id >= 300 && id < 400) return '🌦️';
  if (id >= 500 && id < 600) return '🌧️';
  if (id >= 600 && id < 700) return '❄️';
  if (id >= 700 && id < 800) return '🌫️';
  if (id === 800)             return '☀️';
  if (id === 801)             return '🌤️';
  if (id === 802)             return '⛅';
  if (id === 803)             return '🌥️';
  if (id === 804)             return '☁️';
  return '🌡️';
}

function windDir(deg) {
  return ['N', 'NE', 'E', 'SE', 'S', 'SW', 'W', 'NW'][Math.round(deg / 45) % 8];
}


function uvLabel(uvi) {
  if (uvi <= 2)  return 'Low';
  if (uvi <= 5)  return 'Mod';
  if (uvi <= 7)  return 'High';
  if (uvi <= 10) return 'V.High';
  return 'Extreme';
}

// Convert Unix timestamp to "YYYY-MM-DDTHH:MM" in Auckland time
// (format expected by clock.setSunTimes)
function unixToAucklandISO(ts) {
  const d = new Date(ts * 1000);
  const parts = new Intl.DateTimeFormat('en-NZ', {
    timeZone: 'Pacific/Auckland',
    year: 'numeric', month: '2-digit', day: '2-digit',
    hour: '2-digit', minute: '2-digit', hour12: false,
  }).formatToParts(d);
  const p = {};
  parts.forEach(({ type, value }) => { p[type] = value; });
  return `${p.year}-${p.month}-${p.day}T${String(p.hour).padStart(2, '0')}:${p.minute}`;
}

// Group 3-hour forecast blocks into daily summaries, skipping today
function parseDaily(list) {
  const byDate = new Map();
  const todayKey = new Date().toLocaleDateString('en-CA', { timeZone: 'Pacific/Auckland' });

  for (const item of list) {
    const key = new Date(item.dt * 1000).toLocaleDateString('en-CA', { timeZone: 'Pacific/Auckland' });
    if (key <= todayKey) continue;
    if (!byDate.has(key)) byDate.set(key, []);
    byDate.get(key).push(item);
  }

  return [...byDate.entries()].slice(0, 3).map(([date, blocks]) => {
    const temps = blocks.map(b => b.main.temp);
    const mid   = blocks[Math.floor(blocks.length / 2)];
    return {
      date,
      high: Math.round(Math.max(...temps)),
      low:  Math.round(Math.min(...temps)),
      pop:  Math.round(Math.max(...blocks.map(b => b.pop ?? 0)) * 100),
      icon: owIcon(mid.weather[0].id),
    };
  });
}

function fmtDate(dateStr) {
  return new Date(dateStr + 'T12:00:00').toLocaleDateString('en-NZ', {
    timeZone: 'Pacific/Auckland',
    weekday: 'short',
    day: 'numeric',
    month: 'short',
  });
}

export async function initWeather(clock) {
  const container = document.getElementById('panel-weather');
  container.innerHTML = '<div class="weather-loading">Loading weather…</div>';

  try {
    const [curResult, fcResult, uviResult] = await Promise.allSettled([
      fetch(`${OW}/weather?lat=${LAT}&lon=${LNG}&units=metric&appid=${OPENWEATHER_KEY}`)
        .then(r => { if (!r.ok) throw new Error(`HTTP ${r.status}`); return r.json(); }),
      fetch(`${OW}/forecast?lat=${LAT}&lon=${LNG}&units=metric&appid=${OPENWEATHER_KEY}`)
        .then(r => { if (!r.ok) throw new Error(`HTTP ${r.status}`); return r.json(); }),
      fetch(`${OW}/uvi?lat=${LAT}&lon=${LNG}&appid=${OPENWEATHER_KEY}`)
        .then(r => { if (!r.ok) throw new Error(`HTTP ${r.status}`); return r.json(); }),
    ]);

    if (curResult.status === 'rejected') throw curResult.reason;
    if (fcResult.status  === 'rejected') throw fcResult.reason;

    const cur = curResult.value;
    const fc  = fcResult.value;
    const uvi = uviResult.status === 'fulfilled'
      ? Math.round(uviResult.value.value)
      : null;

    clock.setSunTimes(
      unixToAucklandISO(cur.sys.sunrise),
      unixToAucklandISO(cur.sys.sunset),
    );

    const cond  = cur.weather[0];
    const daily = parseDaily(fc.list);
    const speedKn  = Math.round(cur.wind.speed * 1.944);
    const gustKn   = cur.wind.gust ? Math.round(cur.wind.gust * 1.944) : null;
    const dir      = windDir(cur.wind.deg);
    // Dew point approximation: Td ≈ T - (100 - RH)/5
    const dewPt    = Math.round(cur.main.temp - (100 - cur.main.humidity) / 5);
    const condUC   = cond.description.replace(/^\w/, c => c.toUpperCase());

    const forecastHTML = daily.map(d => `
      <div class="wx-fc">
        <span class="day">${fmtDate(d.date)}</span>
        <span class="em">${d.icon}</span>
        <span class="rain">${d.pop}%</span>
        <span class="hl">${d.high}° <span class="lo">${d.low}°</span></span>
      </div>
    `).join('');

    container.innerHTML = `
      <div class="wx-hero">
        <span class="wx-emoji">${owIcon(cond.id)}</span>
        <div>
          <div class="wx-temp">${Math.round(cur.main.temp)}<span class="deg">°</span></div>
          <div class="wx-cond">${condUC}</div>
        </div>
      </div>

      <div class="wx-grid">
        <div class="wx-card">
          <span class="label">Wind</span>
          <div class="value">${speedKn}<span style="font-size:11px;color:var(--text-dim);font-weight:400;margin-left:3px">kn</span></div>
          <div class="detail">${dir} ${cur.wind.deg}°${gustKn ? ` · ${gustKn} gust` : ''}</div>
          <div class="corner">
            <svg width="14" height="14" viewBox="0 0 24 24" style="transform:rotate(${cur.wind.deg}deg);transition:transform 0.6s">
              <path d="M12 3 L17 13 L12 10 L7 13 Z" fill="currentColor"/>
            </svg>
          </div>
        </div>
        <div class="wx-card">
          <span class="label">UV Index</span>
          <div class="value">${uvi !== null ? uvi : '—'}</div>
          <div class="detail">${uvi !== null ? uvLabel(uvi) : 'No data'}</div>
          <div class="corner">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round">
              <circle cx="12" cy="12" r="4"/>
              <path d="M12 3v2M12 19v2M3 12h2M19 12h2M5.5 5.5l1.4 1.4M17.1 17.1l1.4 1.4M5.5 18.5l1.4-1.4M17.1 6.9l1.4-1.4"/>
            </svg>
          </div>
        </div>
        <div class="wx-card">
          <span class="label">Humidity</span>
          <div class="value">${cur.main.humidity}<span style="font-size:11px;color:var(--text-dim);font-weight:400;margin-left:3px">%</span></div>
          <div class="detail">Dew pt · ${dewPt}°</div>
          <div class="corner">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor">
              <path d="M12 2 C 7 9, 5 13, 5 16 a7 7 0 0 0 14 0 c 0-3 -2-7 -7-14 z" opacity="0.85"/>
            </svg>
          </div>
        </div>
        <div class="wx-card">
          <span class="label">Feels Like</span>
          <div class="value">${Math.round(cur.main.feels_like)}<span style="font-size:11px;color:var(--text-dim);font-weight:400;margin-left:3px">°C</span></div>
          <div class="detail">${cur.main.pressure} hPa</div>
          <div class="corner">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round">
              <path d="M10 4 a2 2 0 0 1 4 0 v9 a4 4 0 1 1 -4 0 z"/>
            </svg>
          </div>
        </div>
      </div>

      <div class="wx-forecast">${forecastHTML}</div>
    `;
  } catch (err) {
    console.error('[weather]', err);
    container.innerHTML = '<div class="weather-unavailable">⚠ Weather unavailable</div>';
  }
}
