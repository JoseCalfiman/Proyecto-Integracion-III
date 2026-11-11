// Funciones puras reutilizables para estadísticas del gerente (sin mocks).
const fechaLocalKey = (date) => {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
};

const mediana = (sorted) => {
  if (sorted.length === 0) return null;
  const m = Math.floor(sorted.length / 2);
  return sorted.length % 2 === 1 ? sorted[m] : (sorted[m - 1] + sorted[m]) / 2;
};

// Nota: el endpoint del backend rellena con 0 los días sin lecturas.
// Estas medidas describen exactamente el conjunto de días entregado por esa API.
export const resumirConsumoDiario = (registros = []) => {
  const valores = (Array.isArray(registros) ? registros : [])
    .map((r) => r?.kwh)
    .filter((v) => v !== null && v !== undefined && Number.isFinite(Number(v)))
    .map(Number);
  if (valores.length === 0) return null;

  const n = valores.length;
  const total = valores.reduce((s, x) => s + x, 0);
  const media = total / n;
  const ordenados = [...valores].sort((a, b) => a - b);
  // Desviación estándar poblacional de los totales diarios del periodo.
  const desviacion = Math.sqrt(valores.reduce((s, x) => s + (x - media) ** 2, 0) / n);
  return { n, total, media, mediana: mediana(ordenados), desviacion };
};

export const prepararEstadisticasAlertas = (registros = [], dias = 7, hoy = new Date()) => {
  const rango = [7, 14, 30].includes(Number(dias)) ? Number(dias) : 7;
  const fin = new Date(hoy);
  const inicio = new Date(fin);
  inicio.setHours(0, 0, 0, 0);
  inicio.setDate(inicio.getDate() - rango + 1);

  const porDia = new Map();
  for (let i = 0; i < rango; i++) {
    const fecha = new Date(inicio);
    fecha.setDate(inicio.getDate() + i);
    const llave = fechaLocalKey(fecha);
    porDia.set(llave, {
      fecha: llave,
      etiqueta: fecha.toLocaleDateString("es-CL", { day: "2-digit", month: "short" }),
      cantidad: 0,
    });
  }

  const camaras = new Map();
  let total = 0;
  for (const alerta of (Array.isArray(registros) ? registros : [])) {
    if (!alerta || !alerta.generation_date) continue;
    const fecha = new Date(alerta.generation_date);
    if (Number.isNaN(fecha.getTime()) || fecha < inicio || fecha > fin) continue;
    const llaveDia = fechaLocalKey(fecha);
    const grupo = porDia.get(llaveDia);
    if (!grupo) continue;
    grupo.cantidad++;
    total++;
    const id = String(alerta.id_chamber ?? alerta.chamber_name ?? "sin-camara");
    const nombre = String(alerta.chamber_name || alerta.id_chamber || "Cámara sin identificar");
    const actual = camaras.get(id) ?? { id, camara: nombre, cantidad: 0 };
    actual.cantidad++;
    camaras.set(id, actual);
  }
  const ranking = [...camaras.values()]
    .sort((a, b) => b.cantidad - a.cantidad || a.camara.localeCompare(b.camara, "es"))
    .slice(0, 5);
  return { total, porDia: [...porDia.values()], ranking, rango };
};