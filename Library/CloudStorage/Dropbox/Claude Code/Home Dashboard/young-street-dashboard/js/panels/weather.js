const API_URL =
  'https://api.open-meteo.com/v1/forecast' +
  '?latitude=-36.4751&longitude=174.7354' +
  '&current=temperature_2m,weather_code,wind_speed_10m' +
  '&daily=weather_code,temperature_2m_max,temperature_2m_min,sunrise,sunset' +
  '&timezone=Pacific%2FAuckland&wind_speed_unit=kmh';

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
  } catch (err) {
    console.error('[weather]', err);
    container.innerHTML = '<div class="weather-unavailable">⚠ Weather unavailable</div>';
  }
}
