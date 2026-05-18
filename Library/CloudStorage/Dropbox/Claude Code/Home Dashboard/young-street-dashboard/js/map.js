const LAT = -36.47509646412374;
const LNG = 174.73539799623094;

export function initMap() {
  const map = L.map('map').setView([LAT, LNG], 17);

  const layers = {
    standard: L.tileLayer(
      'https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',
      {
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
        maxZoom: 19,
      }
    ),
    satellite: L.tileLayer(
      'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
      {
        attribution: 'Tiles &copy; Esri &mdash; Source: Esri, i-cubed, USDA, USGS, AEX, GeoEye, Getmapping, Aerogrid, IGN, IGP, UPR-EGP, and the GIS User Community',
        maxZoom: 19,
      }
    ),
    topo: L.tileLayer(
      'https://{s}.tile.opentopomap.org/{z}/{x}/{y}.png',
      {
        attribution: 'Map data: &copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors, <a href="http://viewfinderpanoramas.org">SRTM</a> | Map style: &copy; <a href="https://opentopomap.org">OpenTopoMap</a> (<a href="https://creativecommons.org/licenses/by-sa/3.0/">CC-BY-SA</a>)',
        maxZoom: 17,
      }
    ),
  };

  // Satellite is the dark-theme default
  layers.satellite.addTo(map);

  L.control.layers({
    'Standard':    layers.standard,
    'Satellite':   layers.satellite,
    'Topographic': layers.topo,
  }, null, { position: 'bottomright' }).addTo(map);

  L.marker([LAT, LNG])
    .addTo(map)
    .bindPopup('<strong>11 Young Street</strong><br>Scotts Landing, Mahurangi East');

  return { map, layers };
}
