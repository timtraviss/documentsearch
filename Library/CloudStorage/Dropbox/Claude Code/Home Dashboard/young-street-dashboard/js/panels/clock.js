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

    document.getElementById('clock-sun').innerHTML = `
      <span>🌅 ${fmt(sunriseISO)}</span>
      <span>🌇 ${fmt(sunsetISO)}</span>
    `;
  }

  return { setSunTimes };
}
