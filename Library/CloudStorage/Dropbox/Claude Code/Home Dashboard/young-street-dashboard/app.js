import { initMap }      from './js/map.js';
import { initTheme }    from './js/theme.js';
import { initClock }    from './js/panels/clock.js';
import { initWeather }  from './js/panels/weather.js';
import { initProperty } from './js/panels/property.js';
import { initTides }    from './js/panels/tides.js';

const { map, layers } = initMap();
initTheme(map, layers);
const clock = initClock();
initWeather(clock);
initProperty();
initTides();
