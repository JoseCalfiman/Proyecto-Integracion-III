// Hook genérico para consultar la API con estado de carga/error y datos de
// respaldo (mock) mientras el backend de Diego no esté disponible en todos
// los endpoints. Cuando el endpoint real responda, esto se usa igual, solo
// que `isFallback` quedará siempre en false.

import { useState, useEffect, useCallback, useRef } from 'react';

// ============================================================
// Normaliza la respuesta de la API para que SIEMPRE sea un array
// cuando el resultado sea una lista. Si es un objeto, busca
// propiedades comunes (data, alertas, camaras, etc.).
// ============================================================
const normalizeData = (result, fallbackData) => {
  // Si ya es un array, devolverlo tal cual
  if (Array.isArray(result)) return result;

  // Si es un objeto, buscar el array dentro de propiedades comunes
  if (result && typeof result === 'object') {
    // Buscar la primera propiedad que sea un array
    const arrayProp = Object.values(result).find((val) => Array.isArray(val));
    if (arrayProp) return arrayProp;
  }

  // Si nada de lo anterior funciona, usar el fallback
  return Array.isArray(fallbackData) ? fallbackData : [];
};

export const useFetch = (fetchFn, deps = [], fallbackData = null) => {
  const [data, setData] = useState(
    Array.isArray(fallbackData) ? fallbackData : fallbackData
  );
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [isFallback, setIsFallback] = useState(false);
  const fetchFnRef = useRef(fetchFn);
  fetchFnRef.current = fetchFn;

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await fetchFnRef.current();

      // Normalizar la respuesta para garantizar que sea un array
      const normalized = normalizeData(result, fallbackData);
      setData(normalized);
      setIsFallback(false);
    } catch (err) {
      setError(err.message || 'Error al conectar con el servidor');
      if (fallbackData !== null) {
        setData(Array.isArray(fallbackData) ? fallbackData : []);
        setIsFallback(true);
      }
    } finally {
      setLoading(false);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps);

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps);

  return { data, loading, error, isFallback, reload: load };
};