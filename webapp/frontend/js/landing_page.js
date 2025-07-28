let tripss=0;

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


async function cargarIndicadores() {
  const fechaAleatoria = generarFechaAleatoria('2014-04'); // Cambia mes aquí

  try {
    const response = await fetch(`${window.env.API_URL}/api/uber-trips/indicators`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({ date_code: fechaAleatoria })
    });

    if (!response.ok) {
      throw new Error('Error al obtener los indicadores');
    }

    const data = await response.json();
    const result = data.result;
   

    // Aquí sigue todo tu código actual (actualización de tarjetas, mapa, etc.)
    document.getElementById('monitor').textContent = formatearFechaLocalLima(result.date);
    document.getElementById('trips').textContent = result.total_trips;
    document.getElementById('anomalies').textContent = result.total_anomalies.toLocaleString();
    document.getElementById('hot_location').textContent = result.hot_location.toLocaleString();
    document.getElementById('rush_hour').textContent = result.rush_hour.toLocaleString() + ':00';

    const rawValue = result.increased_demand_pct ?? 0;
    const porcentaje = rawValue.toLocaleString(undefined, {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2
    }) + '%';

    const container = document.getElementById('increased_demand_pct');
    let icon = '', colorClass = '';

    if (rawValue > 0) {
      icon = '<i class="text-success bi bi-arrow-up-circle me-1"></i>';
    } else if (rawValue < 0) {
      icon = '<i class="text-danger bi bi-arrow-down-circle-fill me-1"></i>';
    } else {
      icon = '<i class="bi bi-dash me-1"></i>';
      colorClass = 'text-success';
    }

    container.innerHTML = `${icon}<span class="${colorClass}">${porcentaje}</span>`;

    // Crear mapa
    const radius = 25;
    const opacity = 0.6;
    const map = L.map('map').setView([40.7128, -74.0060], 10);

    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      attribution: 'Taxi Anomaly Detector'
    }).addTo(map);

    function generarPuntos(cantidad) {
      const puntos = [];
      for (let i = 0; i < cantidad; i++) {
        const lat = 40.7120 + (Math.random() - 0.1) * 1;
        const lng = -74.0060 + (Math.random() - 0.2) * 1;
        const intensidad = Math.floor(Math.random() * 10) + 1;
        puntos.push([lat, lng, intensidad]);
      }
      return puntos;
    }

    const heat = L.heatLayer(generarPuntos(100), {
      radius,
      maxZoom: 9,
      max: 8,
      blur: 8,
      gradient: { 0.4: 'orange', 0.5: 'lime', 0.6: 'yellow', 1: 'red' },
      opacity: 1
    }).addTo(map);

  } catch (error) {
    console.error('Error al cargar indicadores:', error);
  }
}

//Generar UNA fecha aleatoria del mes
function generarFechaAleatoria(mesAño = '2014-04') {
  const dia = String(Math.floor(Math.random() * 30) + 1).padStart(2, '0');
  return `${mesAño}-${dia}`;
}


  // Ejecutar al cargar la página
  window.addEventListener('DOMContentLoaded', cargarIndicadores);

 
