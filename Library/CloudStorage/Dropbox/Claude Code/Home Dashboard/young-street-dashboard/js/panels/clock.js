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
        hour12:   false,
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

  // Called by weather.js once it has fetched today's sunrise/sunset ISO strings.
  // Open-Meteo returns strings like "2026-05-18T06:32" — already NZ local time,
  // no timezone designator. Parsing directly avoids browser-timezone conversion bugs.
  function setSunTimes(sunriseISO, sunsetISO) {
    const fmt = iso => {
      const [, h, m] = iso.match(/T(\d{2}):(\d{2})/);
      return `${h}:${m}`;
    };

    const RISE_SVG = `<svg width="13" height="13" viewBox="0 0 16 16" fill="none" xmlns="http://www.w3.org/2000/svg" style="vertical-align:-1px">
      <circle cx="8" cy="9" r="3" stroke="currentColor" stroke-width="1.4"/>
      <line x1="8" y1="1" x2="8" y2="3.5" stroke="currentColor" stroke-width="1.4" stroke-linecap="round"/>
      <line x1="3.1" y1="4.1" x2="4.9" y2="5.9" stroke="currentColor" stroke-width="1.4" stroke-linecap="round"/>
      <line x1="12.9" y1="4.1" x2="11.1" y2="5.9" stroke="currentColor" stroke-width="1.4" stroke-linecap="round"/>
      <line x1="1" y1="9" x2="3.5" y2="9" stroke="currentColor" stroke-width="1.4" stroke-linecap="round"/>
      <line x1="15" y1="9" x2="12.5" y2="9" stroke="currentColor" stroke-width="1.4" stroke-linecap="round"/>
      <polyline points="5.5,14 8,11.5 10.5,14" stroke="currentColor" stroke-width="1.4" stroke-linecap="round" stroke-linejoin="round" fill="none"/>
    </svg>`;

    const SET_SVG = `<svg width="13" height="13" viewBox="0 0 16 16" fill="none" xmlns="http://www.w3.org/2000/svg" style="vertical-align:-1px">
      <circle cx="8" cy="7" r="3" stroke="currentColor" stroke-width="1.4"/>
      <line x1="8" y1="1" x2="8" y2="3.5" stroke="currentColor" stroke-width="1.4" stroke-linecap="round"/>
      <line x1="3.1" y1="2.1" x2="4.9" y2="3.9" stroke="currentColor" stroke-width="1.4" stroke-linecap="round"/>
      <line x1="12.9" y1="2.1" x2="11.1" y2="3.9" stroke="currentColor" stroke-width="1.4" stroke-linecap="round"/>
      <line x1="1" y1="7" x2="3.5" y2="7" stroke="currentColor" stroke-width="1.4" stroke-linecap="round"/>
      <line x1="15" y1="7" x2="12.5" y2="7" stroke="currentColor" stroke-width="1.4" stroke-linecap="round"/>
      <polyline points="5.5,11 8,13.5 10.5,11" stroke="currentColor" stroke-width="1.4" stroke-linecap="round" stroke-linejoin="round" fill="none"/>
    </svg>`;

    document.getElementById('clock-sun').innerHTML = `
      <span>${RISE_SVG} ${fmt(sunriseISO)}</span>
      <span>${SET_SVG} ${fmt(sunsetISO)}</span>
    `;
  }

  return { setSunTimes };
}
