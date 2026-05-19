const EXPAND_SVG   = `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><polyline points="15 3 21 3 21 9"/><polyline points="9 21 3 21 3 15"/><line x1="21" y1="3" x2="14" y2="10"/><line x1="3" y1="21" x2="10" y2="14"/></svg>`;
const COMPRESS_SVG = `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><polyline points="4 14 10 14 10 20"/><polyline points="20 10 14 10 14 4"/><line x1="10" y1="14" x2="3" y2="21"/><line x1="21" y1="3" x2="14" y2="10"/></svg>`;

export function initFocus() {
  const btn = document.getElementById('btn-focus');
  let hidden = false;

  function update() {
    btn.innerHTML = hidden ? COMPRESS_SVG : EXPAND_SVG;
    btn.setAttribute('aria-label', hidden ? 'Show panels' : 'Hide panels');
    btn.classList.toggle('active', hidden);
    document.body.classList.toggle('panels-hidden', hidden);
  }

  function toggle() {
    hidden = !hidden;
    update();
  }

  btn.addEventListener('click', toggle);

  document.addEventListener('keydown', e => {
    if (e.key !== 'h' && e.key !== 'H') return;
    if (document.activeElement.tagName === 'INPUT') return;
    toggle();
  });

  update();
}
