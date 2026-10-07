// Funciones de formateo reutilizadas en todo el dashboard.

export const formatCLP = (value) =>
  new Intl.NumberFormat('es-CL', {
    style: 'currency',
    currency: 'CLP',
    maximumFractionDigits: 0,
  }).format(value || 0);

export const formatDate = (isoString) => {
  if (!isoString) return '-';
  return new Intl.DateTimeFormat('es-CL', {
    dateStyle: 'short',
    timeStyle: 'short',
  }).format(new Date(isoString));
};

export const formatPercent = (value) => `${Number(value).toFixed(1)}%`;

export const formatTemp = (value) => `${Number(value).toFixed(1)}°C`;

export const formatKwh = (value) => `${Number(value).toFixed(1)} kWh`;
