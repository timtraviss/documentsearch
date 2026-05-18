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
