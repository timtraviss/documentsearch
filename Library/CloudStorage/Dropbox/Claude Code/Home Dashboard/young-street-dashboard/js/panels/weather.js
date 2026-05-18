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

function windArrow(deg) {
  return `<svg width="11" height="11" viewBox="0 0 11 11" xmlns="http://www.w3.org/2000/svg" style="vertical-align:middle;margin-right:3px"><g transform="rotate(${deg},5.5,5.5)"><polygon points="5.5,1 4,8 7,8" fill="currentColor"/></g></svg>`;
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
    const label = cond.description.replace(/^\w/, c => c.toUpperCase());

    const forecastHTML = daily.map(d => `
      <div class="forecast-day">
        <div class="forecast-date">${fmtDate(d.date)}</div>
        <div class="forecast-icon">${d.icon}</div>
        <div class="forecast-pop">🌂 ${d.pop}%</div>
        <div class="forecast-temps">${d.high}° / ${d.low}°</div>
      </div>
    `).join('');

    const speedKmh = Math.round(cur.wind.speed * 3.6);
    const gustKmh  = cur.wind.gust ? Math.round(cur.wind.gust * 3.6) : null;
    const dir      = windDir(cur.wind.deg);

    container.innerHTML = `
      <div class="weather-hero">
        <span class="weather-icon">${owIcon(cond.id)}</span>
        <div>
          <div class="weather-temp">${Math.round(cur.main.temp)}<span class="weather-unit">°C</span></div>
          <div class="weather-condition">${label}</div>
        </div>
      </div>

      <div class="weather-metrics">
        <div class="wx-card">
          <div class="wx-card-label">Wind</div>
          <div class="wx-card-value">${speedKmh}<span class="wx-card-unit"> km/h</span></div>
          <div class="wx-card-sub wx-wind">${windArrow(cur.wind.deg)}${dir}${gustKmh ? ` · ${gustKmh} gust` : ''}</div>
        </div>
        <div class="wx-card">
          <div class="wx-card-label">UV Index</div>
          <div class="wx-card-value">${uvi !== null ? uvi : '—'}</div>
          <div class="wx-card-sub">${uvi !== null ? uvLabel(uvi) : 'No data'}</div>
        </div>
        <div class="wx-card">
          <div class="wx-card-label">Humidity</div>
          <div class="wx-card-value">${cur.main.humidity}<span class="wx-card-unit">%</span></div>
          <div class="wx-card-sub">Cloud ${cur.clouds.all}%</div>
        </div>
        <div class="wx-card">
          <div class="wx-card-label">Feels Like</div>
          <div class="wx-card-value">${Math.round(cur.main.feels_like)}<span class="wx-card-unit">°</span></div>
          <div class="wx-card-sub">${cur.main.pressure} hPa</div>
        </div>
      </div>

      <div class="weather-forecast">${forecastHTML}</div>
    `;
  } catch (err) {
    console.error('[weather]', err);
    container.innerHTML = '<div class="weather-unavailable">⚠ Weather unavailable</div>';
  }
}
