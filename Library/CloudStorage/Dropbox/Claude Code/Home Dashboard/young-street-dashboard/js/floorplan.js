// All pages exported at 2382×1684 px — used to set Leaflet image bounds.
const IMG_W = 2382;
const IMG_H = 1684;
const IMG_BOUNDS = [[0, 0], [IMG_H, IMG_W]];

export function initFloorPlan(map) {
  const toggleBtn = document.getElementById('view-toggle');
  const mapEl     = document.getElementById('map');
  const bg        = document.getElementById('floor-plan-bg');
  const nav       = document.getElementById('floor-plan-nav');
  const pageLabel = document.getElementById('floor-plan-page');
  const prevBtn   = document.getElementById('floor-plan-prev');
  const nextBtn   = document.getElementById('floor-plan-next');

  let pageCount   = 0;
  let currentPage = 1;
  let planActive  = false;
  let planMap     = null;
  let overlay     = null;

  fetch('property.json')
    .then(r => r.json())
    .then(data => {
      pageCount = data?.floorPlan?.pageCount ?? 0;
      if (pageCount > 0) toggleBtn.classList.remove('hidden');
    })
    .catch(() => {});

  function initPlanMap() {
    planMap = L.map(bg, {
      crs: L.CRS.Simple,
      zoomSnap: 0.1,
      zoomDelta: 0.5,
      attributionControl: false,
      zoomControl: false,
    });
    L.control.zoom({ position: 'bottomright' }).addTo(planMap);
  }

  function showPage(n) {
    currentPage = Math.max(1, Math.min(n, pageCount));
    const url = `plans/page-${String(currentPage).padStart(2, '0')}.png`;
    if (overlay) planMap.removeLayer(overlay);
    overlay = L.imageOverlay(url, IMG_BOUNDS).addTo(planMap);
    planMap.fitBounds(IMG_BOUNDS, { padding: [10, 10] });
    pageLabel.textContent = `${currentPage} / ${pageCount}`;
    prevBtn.disabled = currentPage === 1;
    nextBtn.disabled = currentPage === pageCount;
  }

  function showPlans() {
    planActive = true;
    mapEl.style.display = 'none';
    bg.classList.remove('hidden');
    nav.classList.remove('hidden');
    toggleBtn.textContent = '🗺';
    toggleBtn.title = 'Switch to map';
    if (!planMap) {
      initPlanMap();
      requestAnimationFrame(() => showPage(currentPage));
    } else {
      planMap.invalidateSize();
      showPage(currentPage);
    }
  }

  function showMap() {
    planActive = false;
    bg.classList.add('hidden');
    nav.classList.add('hidden');
    mapEl.style.display = '';
    toggleBtn.textContent = '📐';
    toggleBtn.title = 'Switch to floor plans';
    map.invalidateSize();
  }

  toggleBtn.addEventListener('click', () => planActive ? showMap() : showPlans());
  prevBtn.addEventListener('click',   () => showPage(currentPage - 1));
  nextBtn.addEventListener('click',   () => showPage(currentPage + 1));

  document.addEventListener('keydown', e => {
    if (!planActive) return;
    if (e.key === 'ArrowLeft'  || e.key === 'ArrowUp')    showPage(currentPage - 1);
    if (e.key === 'ArrowRight' || e.key === 'ArrowDown')  showPage(currentPage + 1);
    if (e.key === 'Escape') showMap();
  });
}
