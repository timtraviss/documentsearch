import { state, setState } from './state.js';

const ACCENT_PRESETS = [
  { id: 'emerald', label: 'Emerald', hex: '#34d399' },
  { id: 'sky',     label: 'Sky',     hex: '#38bdf8' },
  { id: 'amber',   label: 'Amber',   hex: '#f59e0b' },
  { id: 'rose',    label: 'Rose',    hex: '#f472b6' },
  { id: 'violet',  label: 'Violet',  hex: '#a78bfa' },
  { id: 'coral',   label: 'Coral',   hex: '#f87171' },
];

const DEFAULTS = { theme: 'dark', accent: '#34d399', panelOpacity: 72, blur: 18, vignette: true };

export function initAdmin() {
  const panel   = document.getElementById('admin-panel');
  const scrim   = document.getElementById('admin-scrim');
  const openBtn = document.getElementById('btn-admin');
  const closeBtn= document.getElementById('admin-close');

  // Open / close
  function open()  { panel.classList.add('open');  scrim.classList.add('open');  openBtn.classList.add('active'); }
  function close() { panel.classList.remove('open'); scrim.classList.remove('open'); openBtn.classList.remove('active'); }

  openBtn.addEventListener('click', () => panel.classList.contains('open') ? close() : open());
  closeBtn.addEventListener('click', close);
  scrim.addEventListener('click', close);
  document.addEventListener('keydown', e => { if (e.key === 'Escape') close(); });

  // Theme segmented control
  document.querySelectorAll('[data-theme-btn]').forEach(btn => {
    btn.addEventListener('click', () => {
      const theme = btn.dataset.themeBtn;
      setState({ theme });
      updateThemeBtns();
      // sync header theme button icon
      document.getElementById('btn-theme').innerHTML = theme === 'dark'
        ? `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/></svg>`
        : `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"><circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4.93 4.93l1.41 1.41M17.66 17.66l1.41 1.41M2 12h2M20 12h2M4.93 19.07l1.41-1.41M17.66 6.34l1.41-1.41"/></svg>`;
    });
  });

  function updateThemeBtns() {
    document.querySelectorAll('[data-theme-btn]').forEach(btn => {
      btn.classList.toggle('active', btn.dataset.themeBtn === state.theme);
    });
  }

  // Accent swatches
  const swatchGrid = document.getElementById('accent-swatches');
  swatchGrid.innerHTML = ACCENT_PRESETS.map(p => `
    <button class="swatch ${state.accent.toLowerCase() === p.hex.toLowerCase() ? 'active' : ''}"
            data-hex="${p.hex}" title="${p.label}">
      <span class="swatch-dot" style="background:${p.hex}; box-shadow: 0 0 12px ${p.hex}88"></span>
      <span class="swatch-label">${p.label}</span>
    </button>
  `).join('');

  swatchGrid.addEventListener('click', e => {
    const btn = e.target.closest('.swatch');
    if (!btn) return;
    setAccent(btn.dataset.hex);
  });

  // Hex input
  const hexInput   = document.getElementById('accent-hex-input');
  const hexPreview = document.getElementById('accent-hex-preview');

  hexInput.value = state.accent.toUpperCase();
  hexPreview.style.background = state.accent;

  hexInput.addEventListener('input', () => {
    const v = hexInput.value;
    if (/^#[0-9a-fA-F]{6}$/.test(v)) setAccent(v);
  });

  function setAccent(hex) {
    setState({ accent: hex });
    hexInput.value = hex.toUpperCase();
    hexPreview.style.background = hex;
    swatchGrid.querySelectorAll('.swatch').forEach(btn => {
      btn.classList.toggle('active', btn.dataset.hex.toLowerCase() === hex.toLowerCase());
    });
  }

  // Opacity slider
  const sliderOpacity = document.getElementById('slider-opacity');
  const valOpacity    = document.getElementById('val-opacity');

  sliderOpacity.value = state.panelOpacity;
  valOpacity.textContent = state.panelOpacity;
  updateSliderTrack(sliderOpacity, (state.panelOpacity - 40) / 55 * 100);

  sliderOpacity.addEventListener('input', () => {
    const v = parseInt(sliderOpacity.value, 10);
    valOpacity.textContent = v;
    updateSliderTrack(sliderOpacity, (v - 40) / 55 * 100);
    setState({ panelOpacity: v });
  });

  // Blur slider
  const sliderBlur = document.getElementById('slider-blur');
  const valBlur    = document.getElementById('val-blur');

  sliderBlur.value = state.blur;
  valBlur.textContent = state.blur;
  updateSliderTrack(sliderBlur, state.blur / 40 * 100);

  sliderBlur.addEventListener('input', () => {
    const v = parseInt(sliderBlur.value, 10);
    valBlur.textContent = v;
    updateSliderTrack(sliderBlur, v / 40 * 100);
    setState({ blur: v });
  });

  // Vignette toggle
  const togVignette = document.getElementById('tog-vignette');
  togVignette.classList.toggle('on', state.vignette);
  togVignette.addEventListener('click', () => {
    const next = !state.vignette;
    setState({ vignette: next });
    togVignette.classList.toggle('on', next);
  });

  // Reset
  document.getElementById('admin-reset').addEventListener('click', () => {
    setState({ ...DEFAULTS });
    // Sync all controls
    sliderOpacity.value = DEFAULTS.panelOpacity;
    valOpacity.textContent = DEFAULTS.panelOpacity;
    updateSliderTrack(sliderOpacity, (DEFAULTS.panelOpacity - 40) / 55 * 100);
    sliderBlur.value = DEFAULTS.blur;
    valBlur.textContent = DEFAULTS.blur;
    updateSliderTrack(sliderBlur, DEFAULTS.blur / 40 * 100);
    togVignette.classList.toggle('on', DEFAULTS.vignette);
    setAccent(DEFAULTS.accent);
    updateThemeBtns();
  });

  // Init controls to match persisted state
  updateThemeBtns();
}

function updateSliderTrack(input, pct) {
  input.style.setProperty('--p', pct.toFixed(1) + '%');
}
