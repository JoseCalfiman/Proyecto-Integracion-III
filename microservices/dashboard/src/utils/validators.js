// Validaciones simples reutilizadas en formularios (Cámaras, Usuarios, HACCP).

export const isValidEmail = (email) =>
  /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(String(email || '').trim());

export const isRequired = (value) =>
  value !== undefined && value !== null && String(value).trim() !== '';

export const isPositiveNumber = (value) =>
  value !== '' && !isNaN(value) && Number(value) >= 0;
