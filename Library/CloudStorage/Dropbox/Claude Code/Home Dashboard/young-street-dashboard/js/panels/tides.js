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
