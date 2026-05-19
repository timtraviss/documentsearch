import { state, setState, applyState } from './state.js';

const MOON_SVG = `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/></svg>`;
const SUN_SVG  = `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"><circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4.93 4.93l1.41 1.41M17.66 17.66l1.41 1.41M2 12h2M20 12h2M4.93 19.07l1.41-1.41M17.66 6.34l1.41-1.41"/></svg>`;

export function initTheme(map) {
  const btn = document.getElementById('btn-theme');
  if (!btn) return;

  function updateBtn() {
    btn.innerHTML = state.theme === 'dark' ? MOON_SVG : SUN_SVG;
    // Leaflet needs a size hint after the map container's filter changes
    if (map) setTimeout(() => map.invalidateSize(), 50);
  }

  btn.addEventListener('click', () => {
    setState({ theme: state.theme === 'dark' ? 'light' : 'dark' });
    updateBtn();
  });

  // app.js calls applyState() before us — just sync the button icon
  updateBtn();
}
