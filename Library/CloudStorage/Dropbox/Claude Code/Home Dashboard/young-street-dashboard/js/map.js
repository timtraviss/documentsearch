const LAT = -36.47509646412374;
const LNG = 174.73539799623094;

export function initMap() {
  const map = L.map('map', {
    center: [LAT, LNG],
    zoom: 17,
    zoomControl: false,
    attributionControl: true,
    zoomSnap: 0.5,
  });

  L.tileLayer(
    'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
    { attribution: 'Imagery © Esri', maxZoom: 19 }
  ).addTo(map);

  const icon = L.divIcon({
    className: 'property-marker-wrapper',
    html: '<div class="property-marker"></div>',
    iconSize: [64, 64],
    iconAnchor: [32, 32],
  });
  L.marker([LAT, LNG], { icon, interactive: false }).addTo(map);

  return { map };
}
