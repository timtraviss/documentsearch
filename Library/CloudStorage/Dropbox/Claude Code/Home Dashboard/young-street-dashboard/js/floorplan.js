const FLOOR_PLAN_NAMES = ['Ground Floor', 'Upper Floor', 'Site Plan'];

export function initFloorPlan(map) {
  const btnFloorPlan = document.getElementById('btn-floorplan');
  const stage        = document.getElementById('floorplan-stage');
  const canvas       = document.getElementById('floorplan-canvas');
  const mapEl        = document.getElementById('map');
  const vignetteEl   = document.getElementById('vignette');
  const pager        = document.getElementById('fp-pager');
  const zoom         = document.getElementById('fp-zoom');
  const fpNum        = document.getElementById('fp-num');
  const fpTotal      = document.getElementById('fp-total');
  const fpName       = document.getElementById('fp-name');
  const prevBtn      = document.getElementById('fp-prev');
  const nextBtn      = document.getElementById('fp-next');
  const zoomInBtn    = document.getElementById('fp-zoomin');
  const zoomOutBtn   = document.getElementById('fp-zoomout');
  const resetBtn     = document.getElementById('fp-reset');

  const MAP_SVG = `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><polygon points="1 6 8 3 16 6 23 3 23 18 16 21 8 18 1 21 1 6"/><line x1="8" y1="3" x2="8" y2="18"/><line x1="16" y1="6" x2="16" y2="21"/></svg>`;
  const PLAN_SVG = `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="3" width="18" height="18" rx="1"/><path d="M3 11h18M11 3v18"/></svg>`;

  let pageCount   = 0;
  let currentPage = 0;
  let planActive  = false;
  let tf = { x: 0, y: 0, scale: 0.55 };
  let drag = null;

  function applyTransform() {
    canvas.style.transform = `translate(-50%, -50%) scale(${tf.scale}) translate(${tf.x}px, ${tf.y}px)`;
  }

  function resetTransform() {
    tf = { x: -600, y: -400, scale: 0.55 };
    applyTransform();
  }

  fetch('property.json')
    .then(r => r.json())
    .then(data => {
      pageCount = data?.floorPlan?.pageCount ?? 0;
      fpTotal.textContent = pageCount;
      if (pageCount > 0) {
        btnFloorPlan.classList.remove('hidden');
        btnFloorPlan.innerHTML = PLAN_SVG;
      }
    })
    .catch(() => {});

  function showPage(n) {
    currentPage = Math.max(0, Math.min(n, pageCount - 1));
    const url = `plans/page-${String(currentPage + 1).padStart(2, '0')}.png`;
    canvas.innerHTML = `<img src="${url}" alt="Floor plan page ${currentPage + 1}" style="display:block;max-width:none">`;
    fpNum.textContent = currentPage + 1;
    fpName.textContent = FLOOR_PLAN_NAMES[currentPage] ?? `Page ${currentPage + 1}`;
    prevBtn.disabled = currentPage === 0;
    nextBtn.disabled = currentPage === pageCount - 1;
    resetTransform();
  }

  function enterFloorPlan() {
    planActive = true;
    mapEl.style.display = 'none';
    if (vignetteEl) vignetteEl.style.display = 'none';
    stage.classList.add('visible');
    pager.classList.remove('hidden');
    zoom.classList.remove('hidden');
    btnFloorPlan.innerHTML = MAP_SVG;
    btnFloorPlan.classList.add('active');
    showPage(currentPage);
  }

  function exitFloorPlan() {
    planActive = false;
    stage.classList.remove('visible');
    pager.classList.add('hidden');
    zoom.classList.add('hidden');
    mapEl.style.display = '';
    // Restore vignette if state says it should be visible
    import('./state.js').then(({ state }) => {
      if (vignetteEl) vignetteEl.style.display = state.vignette ? '' : 'none';
    });
    btnFloorPlan.innerHTML = PLAN_SVG;
    btnFloorPlan.classList.remove('active');
    map.invalidateSize();
  }

  btnFloorPlan.addEventListener('click', () => planActive ? exitFloorPlan() : enterFloorPlan());
  prevBtn.addEventListener('click', () => showPage(currentPage - 1));
  nextBtn.addEventListener('click', () => showPage(currentPage + 1));

  zoomInBtn.addEventListener('click',  () => { tf.scale = Math.min(2.5, tf.scale * 1.2); applyTransform(); });
  zoomOutBtn.addEventListener('click', () => { tf.scale = Math.max(0.25, tf.scale * 0.83); applyTransform(); });
  resetBtn.addEventListener('click',   resetTransform);

  // Pan via mouse drag
  stage.addEventListener('mousedown', e => {
    if (e.button !== 0) return;
    drag = { sx: e.clientX, sy: e.clientY, ox: tf.x, oy: tf.y };
    stage.classList.add('dragging');
  });
  window.addEventListener('mousemove', e => {
    if (!drag) return;
    tf.x = drag.ox + (e.clientX - drag.sx) / tf.scale;
    tf.y = drag.oy + (e.clientY - drag.sy) / tf.scale;
    applyTransform();
  });
  window.addEventListener('mouseup', () => {
    if (drag) { drag = null; stage.classList.remove('dragging'); }
  });

  // Zoom via wheel
  stage.addEventListener('wheel', e => {
    e.preventDefault();
    tf.scale = Math.max(0.25, Math.min(2.5, tf.scale * (e.deltaY < 0 ? 1.1 : 0.9)));
    applyTransform();
  }, { passive: false });

  // Keyboard
  document.addEventListener('keydown', e => {
    if (!planActive) return;
    if (e.key === 'ArrowLeft'  || e.key === 'ArrowUp')   showPage(currentPage - 1);
    if (e.key === 'ArrowRight' || e.key === 'ArrowDown')  showPage(currentPage + 1);
    if (e.key === 'Escape') exitFloorPlan();
  });
}
