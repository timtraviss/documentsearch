import { initMap }       from './js/map.js';
import { initTheme }     from './js/theme.js';
import { initAdmin }     from './js/admin.js';
import { initClock }     from './js/panels/clock.js';
import { initWeather }   from './js/panels/weather.js';
import { initProperty }  from './js/panels/property.js';
import { initTides }     from './js/panels/tides.js';
import { initFloorPlan } from './js/floorplan.js';
import { applyState }    from './js/state.js';

applyState();
const { map } = initMap();
initTheme(map);
initAdmin();
const clock = initClock();
initWeather(clock);
initProperty();
initTides();
initFloorPlan(map);
