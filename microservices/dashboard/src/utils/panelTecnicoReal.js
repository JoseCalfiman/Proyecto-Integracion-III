// Adaptadores A3: transforman datos REALES de FastAPI sin crear valores de respaldo.
// Son funciones puras para poder comprobarlas con node --test.

export const prepararCamaras = (rows) => rows.map((r) => ({
  id: r.id_chamber,
  nombre: r.name || 'Sin nombre registrado',
  ubicacion: r.location || null,
  habilitada: typeof r.active === 'boolean' ? r.active : null,
}));

export const prepararAlertas = (rows) => rows.map((r) => ({
  id: r.id_alert,
  camara: r.chamber_name || r.id_chamber || null,
  mensaje: r.message || r.alert_type || 'Sin descripción registrada',
  fecha: r.generation_date || null,
  severidad: r.severity || null,
  estado: r.status || null,
}));

// Los registros de /dashboard/temperature YA son medias por cámara e intervalo.
// Se obtiene la media simple entre cámaras para cada intervalo temporal.
// No se calcula una temperatura ficticia para intervalos sin lecturas.

export const prepararTemperaturas = (rows) => {
  const porInstante = new Map();
  for (const row of rows) {
    const fechaMs = Date.parse(row.timestamp);
    const temp = row.temperature;
    if (!Number.isFinite(fechaMs) || typeof temp !== 'number' || !Number.isFinite(temp)) continue;
    if (!porInstante.has(fechaMs)) porInstante.set(fechaMs, { timestamp: fechaMs, suma: 0, cantidad: 0 });
    const item = porInstante.get(fechaMs);
    item.suma += temp;
    item.cantidad += 1;
  }
  return [...porInstante.values()].sort((a, b) => a.timestamp - b.timestamp).map((item) => ({
    timestamp: item.timestamp,
    hora: new Date(item.timestamp).toLocaleTimeString('es-CL', { hour: '2-digit', minute: '2-digit' }),
    temperatura: Number((item.suma / item.cantidad).toFixed(2)),
    camaras: item.cantidad,
  }));
};

export const prepararSensores = (rows) => rows.map((r) => ({
  id: r.id_sensor ?? r.id ?? null,
  ubicacion: r.ubicacion ?? r.location ?? null,
  tipo: r.tipo ?? r.type ?? null,
  bateria: typeof r.bateria === 'number' ? r.bateria : null,
  ultimaLectura: r.ultima_lectura ?? r.last_reading ?? null,
  estado: r.estado ?? r.status ?? null,
}));

