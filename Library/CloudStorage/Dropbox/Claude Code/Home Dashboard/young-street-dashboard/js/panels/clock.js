export function initClock() {
  const container = document.getElementById('panel-clock');

  container.innerHTML = `
    <div class="clock-time">
      <span id="clock-hhmm">--:--</span><span class="sec" id="clock-sec">:--</span>
    </div>
    <div class="clock-date" id="clock-date">—</div>
    <div class="loc-pill">Mahurangi · NZ</div>
    <div class="clock-sun-row" id="clock-sun-row">
      <div class="sun-block">
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round">
          <circle cx="12" cy="14" r="3.5"/>
          <path d="M12 7v-2M7.5 9.5l-1.4-1.4M16.5 9.5l1.4-1.4M5 14h-2M21 14h-2M3 18h18"/>
        </svg>
        <div>
          <span class="label">Sunrise</span>
          <span id="clock-sunrise">--:--</span>
        </div>
      </div>
      <div class="sun-block">
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round">
          <circle cx="12" cy="11" r="3.5"/>
          <path d="M12 4v2M7.5 6.5l-1.4 1.4M16.5 6.5l1.4 1.4M5 11h-2M21 11h-2M3 18h18M9 14l-2 4M15 14l2 4"/>
        </svg>
        <div>
          <span class="label">Sunset</span>
          <span id="clock-sunset">--:--</span>
        </div>
      </div>
    </div>
  `;

  function pad(n) { return n.toString().padStart(2, '0'); }

  function tick() {
    const now = new Date();

    // Get NZ time components
    const parts = new Intl.DateTimeFormat('en-NZ', {
      timeZone: 'Pacific/Auckland',
      hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false,
      weekday: 'long', day: 'numeric', month: 'long', year: 'numeric',
    }).formatToParts(now);

    const p = {};
    parts.forEach(({ type, value }) => { p[type] = value; });

    document.getElementById('clock-hhmm').textContent = `${p.hour}:${p.minute}`;
    document.getElementById('clock-sec').textContent  = `:${p.second}`;
    document.getElementById('clock-date').textContent =
      `${p.weekday}, ${p.day} ${p.month} ${p.year}`.toUpperCase();
  }

  tick();
  setInterval(tick, 1000);

  // Called by weather.js after sunrise/sunset are fetched (ISO strings: "2026-05-19T07:11")
  function setSunTimes(sunriseISO, sunsetISO) {
    const fmt = iso => {
      const [, h, m] = iso.match(/T(\d{2}):(\d{2})/);
      return `${h}:${m}`;
    };
    document.getElementById('clock-sunrise').textContent = fmt(sunriseISO);
    document.getElementById('clock-sunset').textContent  = fmt(sunsetISO);
  }

  return { setSunTimes };
}
