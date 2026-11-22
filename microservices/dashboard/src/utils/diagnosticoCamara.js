/**
 * Funciones puras para el diagnóstico individual de una cámara.
 * No generan lecturas ni completan datos faltantes con valores ficticios.
 */

export const normalizarLecturas = (rows = []) => {
  if (!Array.isArray(rows)) return [];

  return rows
    .map((row) => {
      const timestampMs = Date.parse(row?.timestamp);
      const temperature = row?.temperature == null ? NaN : Number(row.temperature);

      if (!Number.isFinite(timestampMs) || !Number.isFinite(temperature)) return null;

      return {
        ...row,
        temperature,
        timestampMs,
      };
    })
    .filter(Boolean)
    .sort((a, b) => a.timestampMs - b.timestampMs);
};

const quantileLinear = (sortedValues, probability) => {
  if (!sortedValues.length) return null;
  if (sortedValues.length === 1) return sortedValues[0];

  // Cuantil interpolado tipo 7: posición (n - 1) * p.
  const position = (sortedValues.length - 1) * probability;
  const lowerIndex = Math.floor(position);
  const upperIndex = Math.ceil(position);
  const fraction = position - lowerIndex;

  return sortedValues[lowerIndex]
    + ((sortedValues[upperIndex] - sortedValues[lowerIndex]) * fraction);
};

const medianOf = (sortedValues) => {
  const n = sortedValues.length;
  if (!n) return null;
  const middle = Math.floor(n / 2);
  return n % 2 === 0
    ? (sortedValues[middle - 1] + sortedValues[middle]) / 2
    : sortedValues[middle];
};

/**
 * Estadísticas de la población de lecturas recibidas en el periodo consultado.
 * Desviación estándar poblacional: divide por N, no por N - 1.
 * Atípicos: regla de Tukey, fuera de [Q1 - 1.5*IQR, Q3 + 1.5*IQR].
 */
export const calcularEstadisticasTemperatura = (rows = []) => {
  const lecturas = normalizarLecturas(rows);
  if (!lecturas.length) return null;

  const values = lecturas.map((item) => item.temperature);
  const sorted = [...values].sort((a, b) => a - b);
  const count = values.length;
  const mean = values.reduce((sum, value) => sum + value, 0) / count;
  const median = medianOf(sorted);
  const variance = values.reduce((sum, value) => sum + ((value - mean) ** 2), 0) / count;
  const q1 = quantileLinear(sorted, 0.25);
  const q3 = quantileLinear(sorted, 0.75);
  const iqr = q3 - q1;
  const lowerFence = q1 - (1.5 * iqr);
  const upperFence = q3 + (1.5 * iqr);
  const outliers = lecturas.filter(
    (item) => item.temperature < lowerFence || item.temperature > upperFence,
  );

  return {
    count,
    mean,
    median,
    standardDeviation: Math.sqrt(variance),
    q1,
    q3,
    iqr,
    lowerFence,
    upperFence,
    outliers,
  };
};

export const prepararSerieGrafico = (rows = [], maxPoints = 300) => {
  const lecturas = normalizarLecturas(rows);
  return lecturas.slice(-maxPoints).map((item) => ({
    timestamp: item.timestamp,
    timestampMs: item.timestampMs,
    hora: new Date(item.timestampMs).toLocaleTimeString('es-CL', {
      hour: '2-digit',
      minute: '2-digit',
    }),
    temperatura: item.temperature,
  }));
};

export const nivelRiesgoTexto = (riskLevel) => {
  if (riskLevel == null || riskLevel === '') return 'No informado';
  const normalized = String(riskLevel).trim().toLowerCase();
  const labels = {
    low: 'Bajo', bajo: 'Bajo',
    medium: 'Medio', medio: 'Medio',
    high: 'Alto', alto: 'Alto',
    critical: 'Crítico', critico: 'Crítico', crítico: 'Crítico',
    sin_riesgo: 'Sin riesgo',
  };
  return labels[normalized] || String(riskLevel);
};

export const tendenciaDesdePendiente = (slope) => {
  const value = slope == null ? NaN : Number(slope);
  if (!Number.isFinite(value)) return 'Sin pendiente disponible';
  if (value > 0.01) return 'Temperatura en aumento';
  if (value < -0.01) return 'Temperatura en descenso';
  return 'Temperatura estable';
};