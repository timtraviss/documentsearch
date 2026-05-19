const DEFAULTS = {
  theme:        'dark',
  accent:       '#34d399',
  panelOpacity: 72,
  blur:         18,
  vignette:     true,
};

const STORAGE_KEY = 'ysd-display';

function load() {
  try {
    return { ...DEFAULTS, ...JSON.parse(localStorage.getItem(STORAGE_KEY) || '{}') };
  } catch { return { ...DEFAULTS }; }
}

function save(s) {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(s));
}

export const state = load();

export function setState(patch) {
  Object.assign(state, patch);
  save(state);
  applyState();
}

function hexToRgb(hex) {
  const m = hex.replace('#', '').match(/.{1,2}/g);
  return m ? m.map(x => parseInt(x, 16)) : [52, 211, 153];
}

export function applyState() {
  const r = document.documentElement;
  const s = state;

  // Theme class
  r.classList.toggle('light', s.theme === 'light');

  // Accent + derived colours
  const [rv, gv, bv] = hexToRgb(s.accent);
  r.style.setProperty('--accent',       s.accent);
  r.style.setProperty('--accent-soft',  `rgba(${rv},${gv},${bv},0.10)`);
  r.style.setProperty('--accent-dim',   `rgba(${rv},${gv},${bv},0.28)`);
  r.style.setProperty('--glass-border', `rgba(${rv},${gv},${bv},0.28)`);

  // Panel opacity (affects glass-bg alpha channel)
  const op = s.panelOpacity / 100;
  if (s.theme === 'light') {
    r.style.setProperty('--glass-bg',        `rgba(245, 248, 246, ${op + 0.06})`);
    r.style.setProperty('--glass-bg-strong', `rgba(245, 248, 246, ${Math.min(1, op + 0.2)})`);
  } else {
    r.style.setProperty('--glass-bg',        `rgba(8, 18, 28, ${op})`);
    r.style.setProperty('--glass-bg-strong', `rgba(8, 18, 28, ${Math.min(1, op + 0.16)})`);
  }

  // Blur — apply to every panel element
  document.querySelectorAll('.panel, .fp-pager, .fp-zoom, .ctrl-btn, .admin-panel').forEach(el => {
    el.style.backdropFilter        = `blur(${s.blur}px) saturate(1.4)`;
    el.style.webkitBackdropFilter  = `blur(${s.blur}px) saturate(1.4)`;
  });

  // Vignette visibility
  const vignette = document.getElementById('vignette');
  if (vignette) vignette.style.display = s.vignette ? '' : 'none';
}
