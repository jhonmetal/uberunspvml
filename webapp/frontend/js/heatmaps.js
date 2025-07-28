   // Crear mapa
    const radius = 25;     // Tamaño del área de influencia de cada punto
    const opacity = 0.6;   // Transparencia del heatmap
    // 1. Map Initialization
    const map = L.map('map').setView([40.7128, -74.0060], 11); // Center on New York with zoom 12

    // OpenStreetMap base layer
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
    }).addTo(map);

    // Global variables to store data and control state
    let allData = []; // Stores all loaded anomaly data
    let filteredData = []; // Stores data after applying filters (date, etc.)
    let timeAxis = []; // Array of unique sorted timestamps for the date slider
    let heatLayer; // heatmap puro
    let anomalyTooltipLayer; // Capa para markers de tooltips
    let heatmapAnomalousLayer;
    let heatmapNormalLayer;
    let dateInput, rangeHour, rangeHourValue;
document.addEventListener("DOMContentLoaded", () => {
  dateInput = document.getElementById("date-value");
  rangeHour = document.getElementById("range-hour");
  rangeHourValue = document.getElementById("range-hour-value");

  const defaultDate = "2014-04-15";
  dateInput.value = defaultDate;

  const dateStr = new Date(defaultDate).toISOString().slice(0, 10);
  loadJSONData(dateStr);
  cargarIndicadores(dateStr);
  cargarHistoryEvents(dateStr)

  dateInput.addEventListener("change", () => {
    const selectedDate = new Date(dateInput.value).toISOString().slice(0, 10);
    loadJSONData(selectedDate);
    cargarIndicadores(selectedDate);
    cargarHistoryEvents(selectedDate);
  });

  rangeHour.addEventListener("input", () => {
    rangeHourValue.textContent = rangeHour.value;
    applyFilters();
  });
});




    async function loadJSONData(dateStr) {
    //console.log("🚀 Ejecutando función loadJSONData()");
   // console.log("📅 Solicitando datos para la fecha:", dateStr);
  try {
    const response = await fetch(`${window.env.API_URL}/api/uber-trips/values`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ date_code: dateStr })
    });

    if (!response.ok) {
      throw new Error('Error al obtener datos.');
    }

    const apiData = await response.json();
const anomalousRaw = apiData.result?.anomalous?.data ?? [];
const anomalousTime = apiData.result?.anomalous?.time_index ?? [];
const normalRaw = apiData.result?.non_anomalous?.data ?? [];
const normalTime = apiData.result?.non_anomalous?.time_index ?? [];



const anomalous = extractPoints(anomalousRaw).map(([lat, lng], i) => ({
  lat, lng,
  value: 10,
  type: 'Anomalía',
  level: 'critical',
  timestamp: new Date(anomalousTime[i % anomalousTime.length] ?? Date.now()),
  message: `Anomalía detectada el ${anomalousTime[i % anomalousTime.length] ?? 'desconocido'}`
}));

const normal = extractPoints(normalRaw).map(([lat, lng], i) => ({
  lat, lng,
  value: 2,
  type: 'Normal',
  level: 'info',
  timestamp: new Date(normalTime[i % normalTime.length] ?? Date.now()),
  message: `Dato normal detectado el ${normalTime[i % normalTime.length] ?? 'desconocido'}`
}));


 allData = [...anomalous, ...normal];
allData.sort((a, b) => a.timestamp - b.timestamp);
filteredData = allData; // ✅ Ahora sí, después de llenar y ordenar allData

timeAxis = [...new Set(allData.map(a => a.timestamp.getTime()))]
  .sort((a, b) => a - b)
  .map(t => new Date(t));


//updateCharts(filteredData);
updateAlertList(filteredData);
applyFilters();

   } catch (error) {
    console.error("❌ Error:", error);
    
  }
}
function formatearFechaLocalLima(fechaStr) {
  const [año, mes, dia] = fechaStr.split('-').map(Number);
  // mes - 1 porque en JS los meses van de 0 a 11
  const fecha = new Date(año, mes - 1, dia);

  const opciones = {
    weekday: 'long',
    day: '2-digit',
    month: 'long',
    year: 'numeric',
    timeZone: 'America/Lima'
  };

  const fechaFormateada = new Intl.DateTimeFormat('es-PE', opciones).format(fecha);
  const fechaConDel = fechaFormateada.replace(/ de (\d{4})$/, ' del $1');
  return fechaConDel.charAt(0).toUpperCase() + fechaConDel.slice(1);
}

async function cargarIndicadores(dateStr) {
  if (!dateStr) {
    console.warn('⚠️ Fecha no proporcionada a cargarIndicadores');
    return;
  }

  try {
    const response = await fetch(`${window.env.API_URL}/api/uber-trips/indicators`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({ date_code: dateStr })
    });

    if (!response.ok) {
      const errorData = await response.json();
      throw new Error('Error al obtener los indicadores');
    }

    const data = await response.json();

    const result = data.result;
    if (!result) {
      throw new Error('La respuesta no contiene el campo "result"');
    }

    // 👇 Mostrar indicadores
    document.getElementById('trips').textContent = result.total_trips ?? 0;
    document.getElementById('anomalies').textContent = result.total_anomalies ?? 0;
    document.getElementById('hot_location').textContent = result.hot_location ?? '';
    document.getElementById('rush_hour').textContent = (result.rush_hour ?? '-') + ':00';

   

    const rawValue = result.increased_demand_pct ?? 0;
const porcentaje = rawValue.toLocaleString(undefined, {
  minimumFractionDigits: 2,
  maximumFractionDigits: 2
}) + '%';

const container = document.getElementById('increased_demand_pct');

let icon = '';
let colorClass = '';

if (rawValue > 0) {
  icon = '<i class="bi bi-arrow-up-short me-1"></i>';
  colorClass = 'text-success';
} else if (rawValue < 0) {
  icon = '<i class="bi bi-arrow-down-short me-1"></i>';
  colorClass = 'text-danger';
} else {
  icon = '<i class="bi bi-dash me-1"></i>';
  colorClass = 'text-secondary';
}

// Usamos innerHTML para insertar HTML (ícono + valor con color)
container.innerHTML = `${icon}<span class="${colorClass}">${porcentaje}</span>`;


  } catch (error) {
  }
}

async function cargarHistoryEvents(dateStr) {
  if (!dateStr) {
    console.warn('⚠️ Fecha no proporcionada a cargarIndicadores');
    return;
  }

  try {
    const response = await fetch(`${window.env.API_URL}/api/uber-trips/history_events`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ date_code: dateStr })
    });

  //  console.log("📤 Enviando a history_events:", JSON.stringify({ date_code: dateStr }));

    if (!response.ok) {
      const errorData = await response.json();
   //   console.error('📥 Error del servidor:', errorData);
      throw new Error('Error al obtener los indicadores');
    }

    const data = await response.json();
    const result = data.result;


    const container = document.getElementById('historyEventsContainer');
    container.innerHTML = ''; // Limpiar contenido anterior

    if (!result || !Array.isArray(result) || result.length === 0) {
      container.innerHTML = '<p class="text-muted">No se encontraron eventos históricos para esta fecha.</p>';
      return;
    }

result.forEach(event => {
  const item = document.createElement('div');
  item.className = 'anomaly-alert d-flex tooltip-hover justify-content-between align-items-center mb-2 p-3 rounded shadow-sm border border-light bg-white';

  item.innerHTML = `
   <div class="tooltip-text">Fecha en la que se detectaron anomalías en la demanda.</div>
    <div>
      <div class="fw-semibold text-dark"><i class="bi bi-calendar-event me-0 text-primary"></i> ${formatearFechaLocalLima(event.date) || 'Desconocida'}</div>
      <small class="text-muted">Normal: <span class="text-success fw-bold">${event.total_normal ?? 0}</span></small> |
      <small class="text-muted">Anomalías: <span class="text-danger fw-bold">${event.total_anomalies ?? 0}</span></small>
    </div>
    <div>
      <i class="bi bi-arrow-right-circle text-secondary"></i>
    </div>
  `;

  container.appendChild(item);
});



  } catch (error) {
    console.error('Error al cargar indicadores:', error);
  }
}


    /**
     * Main function to apply all active filters (date, radius, opacity) to the data.
     * Updates the heatmap, charts, and stats based on the filtered data.
     */

function applyFilters() {
 rangeHour = document.getElementById("range-hour");
 rangeHourValue = document.getElementById("range-hour-value");

  const selectedHour = parseInt(rangeHour.value);
    filteredData = allData.filter(d => d.timestamp.getHours() === selectedHour);
    

   

  // Limpia las capas previas si existen
  if (heatmapNormalLayer) {
    map.removeLayer(heatmapNormalLayer);
    heatmapNormalLayer = filteredData;
  }

  if (heatmapAnomalousLayer) {
    map.removeLayer(heatmapAnomalousLayer);
    heatmapAnomalousLayer = null;
  }

  if (anomalyTooltipLayer) {
    map.removeLayer(anomalyTooltipLayer);
    anomalyTooltipLayer = null;
  }

  // Separar anomalías y normales
  const anomalousData = filteredData
    .filter(d => d.level === 'critical' || d.level === 'warning')
    .map(d => [d.lat, d.lng, d.value]);

  const normalData = filteredData
    .filter(d => d.level === 'info')
    .map(d => [d.lat, d.lng, d.value]);

  // Agrega la nueva capa de normales (fondo)
  
  heatmapNormalLayer = L.heatLayer(normalData, {
    radius,
    maxZoom: 10,
    max: 8,
    blur: 8,
    gradient: { 0.2: 'blue', 0.8: 'lime', 1.0: 'yellow' },
    opacity: opacity
  }).addTo(map);

  // Agrega la nueva capa de anomalías (por encima)
  heatmapAnomalousLayer = L.heatLayer(anomalousData, {
    radius,
    maxZoom: 10,
    max: 8,
    blur: 8,
    gradient: { 0.4: 'red', 0.6: 'red', 0.1: 'red' },
    opacity: opacity
  }).addTo(map);

  // Tooltips para anomalías
  anomalyTooltipLayer = L.layerGroup();

  function jitter(value) {
    return value + (Math.random() - 0.5) * 0.0003; // Ruido leve
  }

  filteredData
    .filter(d => d.level === 'critical' || d.level === 'warning')
    .forEach((d) => {
      const lat = jitter(d.lat);
      const lng = jitter(d.lng);

      const marker = L.circleMarker([lat, lng], {
        radius: 4,
        color: 'blue',
        fillColor: 'blue',
        fillOpacity: 0.5,
        weight: 1
      });

      marker.bindTooltip(
        `<strong>${d.message}</strong><br><strong>Lat:</strong> ${d.lat}<br><strong>Lng:</strong> ${d.lng}<br><strong>Nivel:</strong> ${d.level}`,
        {
          permanent: false,
          direction: 'top',
          offset: [0, -5],
          opacity: 0.9
        }
      );

      anomalyTooltipLayer.addLayer(marker);
    });
     

  anomalyTooltipLayer.addTo(map);
}


    /**
     * Updates the list of recent alerts in the sidebar.
     * @param {Array} data - The data to use for alerts.
     */
function updateAlertList(data) {
  const alertList = document.getElementById('alert-list');
  alertList.innerHTML = '';

  if (!Array.isArray(data)) {
  //  console.warn("⚠️ updateAlertList: 'data' no es un arreglo:", data);
    alertList.innerHTML = '<p class="text-muted">No hay datos de alertas.</p>';
    return;
  }

  // Filtrar y ordenar
  const sortedAnomalies = [...data]
    .filter(a => a.level === 'critical' || a.level === 'warning')
    .sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp))
    .slice(0, 10);

  if (sortedAnomalies.length === 0) {
    alertList.innerHTML = '<p class="text-muted">No hay alertas recientes.</p>';
    return;
  }

  sortedAnomalies.forEach(anomaly => {
    const alertDiv = document.createElement('div');
    alertDiv.className = `anomaly-alert alert ${anomaly.level === 'critical' ? 'alert-danger' : 'alert-warning'} mb-2`;

    const fecha = new Date(anomaly.timestamp);

    const opciones = {
      weekday: 'long',
      day: '2-digit',
      month: 'long',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
      hour12: false,
      timeZone: 'America/Lima'
    };

    const fechaFormateada = new Intl.DateTimeFormat('es-PE', opciones).format(fecha);
    const fechaConDel = fechaFormateada.replace(/ de (\d{4})/, ' del $1');

    alertDiv.innerHTML = `
      <strong class="alert-strong">${anomaly.type}</strong>: <small class="bi bi-calendar-event me-0 text-primary alert-small text-muted"> ${fechaConDel.charAt(0).toUpperCase() + fechaConDel.slice(1)}</small><br>
     
    `;

    alertList.appendChild(alertDiv);
  });
}


    /**
     * Flattens any structure and returns up to `max` [lat,lng] pairs.
     * Also accepts {lat,lng} objects.
     * @param {Array|Object} raw - The raw data to extract points from.
     * @param {number} max - The maximum number of points to extract.
     * @returns {Array<[number, number]>} An array of [latitude, longitude] pairs.
     */
function extractPoints(raw) {
  const out = [];
  const stack = Array.isArray(raw) ? [...raw] : [raw];

  while (stack.length) {
    const item = stack.pop();

    if (item && typeof item === 'object' && !Array.isArray(item)) {
      const { lat, lng } = item;
      if (Number.isFinite(+lat) && Number.isFinite(+lng)) {
        out.push([+lat, +lng]);
      } else {
        Object.values(item).forEach(v => stack.push(v));
      }
      continue;
    }

    if (Array.isArray(item) && item.length === 2 &&
        Number.isFinite(+item[0]) && Number.isFinite(+item[1])) {
      out.push([+item[0], +item[1]]);
    } else if (Array.isArray(item)) {
      stack.push(...item);
    }
  }

  return out;
}