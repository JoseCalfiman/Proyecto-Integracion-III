import React, { useState, useEffect, useMemo } from 'react';
import {
  ThermometerSnowflake, Save, Check, AlertTriangle, RefreshCw, Info,
} from 'lucide-react';
import { useFetch } from '../../hooks/useApi';
import { getReglasHaccp, actualizarReglasPorCamara } from '../../api/haccp';

// ============================================================
// CONFIGURACIÓN
// ============================================================
// Límites del backend (schemas.HaccpRuleUpdate)
const TEMP_MIN = -50;
const TEMP_MAX = 50;
const TOL_MIN = 1;
const TOL_MAX = 1440;

const severidadConfig = {
  bajo: { label: 'Bajo', activo: 'bg-gray-100 border-gray-300 text-gray-700' },
  medio: { label: 'Medio', activo: 'bg-blue-50 border-blue-300 text-blue-700' },
  alto: { label: 'Alto', activo: 'bg-orange-50 border-orange-300 text-orange-700' },
  critico: { label: 'Crítico', activo: 'bg-red-50 border-red-300 text-red-700' },
};

// ============================================================
// HELPERS
// ============================================================
const parseNum = (value) => (String(value).trim() === '' ? NaN : Number(value));
const round2 = (n) => Math.round(n * 100) / 100;

const reglaToForm = (regla) => ({
  temp_max: String(regla.temp_max),
  temp_min: String(regla.temp_min),
  tiempo_tolerancia: String(regla.tiempo_tolerancia),
  severidad: regla.severidad,
  activa: regla.activa,
});

// Valores tal como se enviarán al backend (temperaturas con 2 decimales).
const normalizar = (form) => ({
  temp_max: round2(parseNum(form.temp_max)),
  temp_min: round2(parseNum(form.temp_min)),
  tiempo_tolerancia: parseNum(form.tiempo_tolerancia),
  severidad: form.severidad,
  activa: form.activa,
});

const validar = (valores) => {
  const errores = {};
  const { temp_max: max, temp_min: min, tiempo_tolerancia: tol } = valores;
  const rangoTemp = `Debe estar entre ${TEMP_MIN} y ${TEMP_MAX} °C`;
  if (!Number.isFinite(max)) errores.temp_max = 'Ingresa un número';
  else if (max < TEMP_MIN || max > TEMP_MAX) errores.temp_max = rangoTemp;
  if (!Number.isFinite(min)) errores.temp_min = 'Ingresa un número';
  else if (min < TEMP_MIN || min > TEMP_MAX) errores.temp_min = rangoTemp;
  if (!errores.temp_max && !errores.temp_min && min >= max) {
    errores.temp_min = 'Debe ser menor que la temperatura máxima';
  }
  if (!Number.isInteger(tol)) errores.tiempo_tolerancia = 'Ingresa un número entero de minutos';
  else if (tol < TOL_MIN || tol > TOL_MAX) errores.tiempo_tolerancia = `Debe estar entre ${TOL_MIN} y ${TOL_MAX} minutos`;
  if (!severidadConfig[valores.severidad]) errores.severidad = 'Selecciona un nivel de severidad';
  return errores;
};

const mismosValores = (a, b) =>
  a.temp_max === b.temp_max && a.temp_min === b.temp_min && a.tiempo_tolerancia === b.tiempo_tolerancia
  && a.severidad === b.severidad && a.activa === b.activa;

const formatearFecha = (iso) => {
  const fecha = new Date(iso);
  return Number.isNaN(fecha.getTime()) ? iso : fecha.toLocaleString('es-CL', { dateStyle: 'short', timeStyle: 'short' });
};

const etiquetaCamara = (c) => {
  const nombre = c.camara || 'Cámara sin nombre';
  if (!c.has_rule) return `${nombre} — sin regla`;
  if (!c.activa) return `${nombre} — inactiva`;
  return nombre;
};

// ============================================================
// CAMPO NUMÉRICO (input + slider de apoyo)
// ============================================================
const CampoNumerico = ({ id, label, ayuda, unidad, value, onChange, min, max, step, error }) => {
  const numero = parseNum(value);
  const posicion = Number.isFinite(numero) ? Math.min(max, Math.max(min, numero)) : min;
  return (
    <div className="mb-6">
      <label htmlFor={id} className="block text-xs text-gray-500 mb-2">{label}</label>
      <div className="flex items-center gap-4">
        <input
          type="range"
          min={min}
          max={max}
          step={step}
          value={posicion}
          onChange={(e) => onChange(e.target.value)}
          className="flex-1 accent-green-500"
          aria-hidden="true"
          tabIndex={-1}
        />
        <div className="flex items-center gap-1">
          <input
            id={id}
            type="number"
            inputMode="decimal"
            min={min}
            max={max}
            step={step}
            value={value}
            onChange={(e) => onChange(e.target.value)}
            aria-invalid={Boolean(error)}
            aria-describedby={`${id}-ayuda${error ? ` ${id}-error` : ''}`}
            className={`w-24 border rounded-lg px-3 py-1.5 text-sm text-center font-medium focus:outline-none focus:ring-2 ${
              error ? 'border-red-300 focus:ring-red-400' : 'border-gray-200 focus:ring-green-500'
            }`}
          />
          <span className="text-sm text-gray-500">{unidad}</span>
        </div>
      </div>
      {error && <p id={`${id}-error`} className="text-xs text-red-600 mt-2">{error}</p>}
      <p id={`${id}-ayuda`} className="text-xs text-gray-400 mt-2">{ayuda}</p>
    </div>
  );
};

// ============================================================
// COMPONENTE
// ============================================================
const HaccpRulesView = () => {
  const { data: camaras, loading, error, reload } = useFetch(getReglasHaccp, []);

  const [selectedId, setSelectedId] = useState(null);
  // Respuesta del último PUT; se usa hasta que la lista recargada la reemplace.
  const [guardada, setGuardada] = useState(null); // { lista, regla }
  const [edicion, setEdicion] = useState(null); // { id, form } con los cambios del usuario
  const [guardando, setGuardando] = useState(false);
  const [aviso, setAviso] = useState(null); // { tipo: 'exito' | 'error', texto }

  const lista = useMemo(() => (Array.isArray(camaras) ? camaras : []), [camaras]);

  // Cámara seleccionada (ids como string: UUID). Sin selección válida, la primera.
  const camaraActual = lista.find((c) => String(c.camara_id) === selectedId) ?? lista[0] ?? null;
  const idActual = camaraActual ? String(camaraActual.camara_id) : null;
  const base = guardada && guardada.lista === camaras && String(guardada.regla.camara_id) === idActual
    ? guardada.regla
    : camaraActual; // regla cargada: referencia para "cambios pendientes"
  const form = useMemo(() => {
    if (!base) return null;
    return edicion?.id === idActual ? edicion.form : reglaToForm(base);
  }, [base, edicion, idActual]);

  const valores = useMemo(() => (form ? normalizar(form) : null), [form]);
  const errores = useMemo(() => (valores ? validar(valores) : {}), [valores]);
  const hayErrores = Object.keys(errores).length > 0;
  const hayCambios = Boolean(base && valores && !mismosValores(valores, normalizar(reglaToForm(base))));
  const bloqueado = Boolean(error) || !form;
  // Una cámara sin regla se puede guardar con los valores sugeridos para crearla.
  const puedeGuardar = !bloqueado && !guardando && !hayErrores && (hayCambios || !base?.has_rule);

  // Avisar al cerrar o recargar la pestaña con cambios sin guardar.
  useEffect(() => {
    if (!hayCambios) return undefined;
    const handler = (e) => {
      e.preventDefault();
      e.returnValue = '';
    };
    window.addEventListener('beforeunload', handler);
    return () => window.removeEventListener('beforeunload', handler);
  }, [hayCambios]);

  // El aviso de éxito se oculta solo.
  useEffect(() => {
    if (aviso?.tipo !== 'exito') return undefined;
    const timer = setTimeout(() => setAviso(null), 4000);
    return () => clearTimeout(timer);
  }, [aviso]);

  const actualizar = (campo, valor) => {
    setEdicion({ id: idActual, form: { ...form, [campo]: valor } });
    if (aviso?.tipo === 'exito') setAviso(null);
  };

  const handleCambiarCamara = (id) => {
    const camara = lista.find((c) => String(c.camara_id) === id);
    if (!camara) return;
    if (hayCambios && !window.confirm('Hay cambios sin guardar en esta cámara. ¿Descartarlos y cambiar de cámara?')) return;
    setSelectedId(String(camara.camara_id));
    setEdicion(null);
    setAviso(null);
  };

  const handleGuardar = async () => {
    if (!base || !puedeGuardar) return;
    if (base.has_rule && base.activa && !valores.activa
      && !window.confirm(`Al desactivar el monitoreo, "${base.camara}" dejará de generar alertas HACCP. ¿Deseas continuar?`)) {
      return;
    }
    setGuardando(true);
    setAviso(null);
    try {
      const guardadaApi = await actualizarReglasPorCamara(base.camara_id, valores);
      setSelectedId(idActual);
      setGuardada({ lista: camaras, regla: guardadaApi });
      setEdicion(null);
      setAviso({ tipo: 'exito', texto: 'Reglas guardadas' });
      reload();
    } catch (err) {
      setAviso({ tipo: 'error', texto: err.message || 'No se pudieron guardar las reglas' });
    } finally {
      setGuardando(false);
    }
  };

  const handleCancelar = () => {
    setEdicion(null);
    setAviso(null);
  };

  // ============================================================
  // ESTADOS DE CARGA / VACÍO
  // ============================================================
  const cargandoInicial = loading && !Array.isArray(camaras);

  return (
    <div>
      {/* ==================================================== */}
      {/* HEADER SUPERIOR */}
      {/* ==================================================== */}
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold text-gray-800">Configuración Reglas HACCP</h1>
        <span className="text-xs font-medium px-3 py-1 rounded-full bg-yellow-100 text-yellow-700">
          Acceso: Gerente
        </span>
      </div>

      {error && (
        <div role="alert" className="flex items-center justify-between gap-4 bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg mb-6 text-sm">
          <div className="flex items-center gap-2">
            <AlertTriangle size={18} />
            <span>No se pudieron cargar las reglas HACCP: {error}</span>
          </div>
          <button
            type="button"
            onClick={reload}
            disabled={loading}
            className="flex items-center gap-2 px-3 py-1.5 rounded-lg border border-red-300 bg-white font-medium hover:bg-red-100 disabled:opacity-50"
          >
            <RefreshCw size={14} className={loading ? 'animate-spin' : ''} />
            Reintentar
          </button>
        </div>
      )}

      {cargandoInicial && (
        <div className="bg-white p-6 rounded-lg shadow-md mb-6 flex items-center gap-2 text-sm text-gray-500">
          <RefreshCw size={16} className="animate-spin" />
          Cargando reglas HACCP...
        </div>
      )}

      {!cargandoInicial && !error && lista.length === 0 && (
        <div className="bg-white p-6 rounded-lg shadow-md mb-6 text-sm text-gray-500">
          No hay cámaras activas para configurar.
        </div>
      )}

      {form && (
        <fieldset disabled={bloqueado} className="min-w-0 disabled:opacity-60">
          {/* ==================================================== */}
          {/* SELECCIONAR CÁMARA */}
          {/* ==================================================== */}
          <div className="bg-white p-6 rounded-lg shadow-md mb-6">
            <label htmlFor="haccp-camara" className="block text-lg font-semibold text-gray-800 mb-1">
              Seleccionar Cámara
            </label>
            <p className="text-sm text-gray-500 mb-4">
              Elija la cámara frigorífica para configurar los parámetros HACCP de monitoreo continuo.
            </p>
            <select
              id="haccp-camara"
              value={idActual ?? ''}
              onChange={(e) => handleCambiarCamara(e.target.value)}
              className="w-full border border-gray-200 rounded-lg px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-green-500"
            >
              {lista.map((c) => (
                <option key={c.camara_id} value={String(c.camara_id)}>
                  {etiquetaCamara(c)}
                </option>
              ))}
            </select>

            <p className="text-xs text-gray-500 mt-3">
              {base?.has_rule && base.modified_by_name && base.review_date
                ? `Última modificación: ${base.modified_by_name} · ${formatearFecha(base.review_date)}`
                : 'Sin modificaciones registradas'}
            </p>

            {base && !base.has_rule && (
              <div className="flex items-start gap-2 mt-4 bg-yellow-50 border border-yellow-200 text-yellow-800 px-4 py-3 rounded-lg text-sm">
                <Info size={18} className="shrink-0 mt-0.5" />
                <span>
                  Sin regla configurada: esta cámara no genera alertas HACCP. Revisa los valores sugeridos y guarda para crear la regla.
                </span>
              </div>
            )}

            {/* Switch de Estado */}
            <div className="flex items-center justify-between mt-6 pt-4 border-t border-gray-100">
              <div>
                <p id="haccp-estado-label" className="font-medium text-gray-700 text-sm">Estado de Reglas HACCP</p>
                <p id="haccp-estado-ayuda" className="text-xs text-gray-500">
                  Activar o desactivar el monitoreo de reglas para esta cámara
                </p>
              </div>
              <div className="flex items-center gap-3">
                <button
                  type="button"
                  role="switch"
                  aria-checked={form.activa}
                  aria-labelledby="haccp-estado-label"
                  aria-describedby="haccp-estado-ayuda"
                  onClick={() => actualizar('activa', !form.activa)}
                  className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors focus:outline-none focus:ring-2 focus:ring-green-500 focus:ring-offset-2 ${
                    form.activa ? 'bg-green-500' : 'bg-gray-300'
                  }`}
                >
                  <span
                    className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                      form.activa ? 'translate-x-6' : 'translate-x-1'
                    }`}
                  />
                </button>
                <span className={`text-sm font-medium ${form.activa ? 'text-green-600' : 'text-gray-500'}`}>
                  {form.activa ? 'Activo' : 'Inactivo'}
                </span>
              </div>
            </div>
          </div>

          {/* ==================================================== */}
          {/* LAYOUT DE 2 COLUMNAS */}
          {/* ==================================================== */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
            {/* LÍMITES DE TEMPERATURA */}
            <div className="bg-white p-6 rounded-lg shadow-md">
              <div className="flex items-center gap-2 mb-6">
                <ThermometerSnowflake size={20} className="text-green-600" />
                <h2 className="font-semibold text-gray-800">Límites de Temperatura</h2>
              </div>

              <CampoNumerico
                id="haccp-temp-max"
                label="Temperatura Máxima Crítica (°C)"
                ayuda="Límite superior HACCP: sobre esta temperatura se genera alerta."
                unidad="°C"
                value={form.temp_max}
                onChange={(v) => actualizar('temp_max', v)}
                min={TEMP_MIN}
                max={TEMP_MAX}
                step={0.1}
                error={errores.temp_max}
              />
              <CampoNumerico
                id="haccp-temp-min"
                label="Temperatura Mínima Crítica (°C)"
                ayuda="Límite inferior HACCP: bajo esta temperatura también se genera alerta."
                unidad="°C"
                value={form.temp_min}
                onChange={(v) => actualizar('temp_min', v)}
                min={TEMP_MIN}
                max={TEMP_MAX}
                step={0.1}
                error={errores.temp_min}
              />
              <p className="text-xs text-gray-400">Las temperaturas se guardan con un máximo de 2 decimales.</p>
            </div>

            {/* REGLAS DE TOLERANCIA */}
            <div className="bg-white p-6 rounded-lg shadow-md">
              <div className="flex items-center gap-2 mb-6">
                <AlertTriangle size={20} className="text-red-500" />
                <h2 className="font-semibold text-gray-800">Reglas de Tolerancia</h2>
              </div>

              <CampoNumerico
                id="haccp-tolerancia"
                label="Tiempo de Tolerancia (Minutos)"
                ayuda="Tiempo permitido fuera de rango antes de alertar (ej. ciclos de deshielo)."
                unidad="min"
                value={form.tiempo_tolerancia}
                onChange={(v) => actualizar('tiempo_tolerancia', v)}
                min={TOL_MIN}
                max={TOL_MAX}
                step={1}
                error={errores.tiempo_tolerancia}
              />

              {/* Nivel de Severidad */}
              <div role="group" aria-labelledby="haccp-severidad-label">
                <p id="haccp-severidad-label" className="block text-xs text-gray-500 mb-2">
                  Nivel de Severidad de Alarma
                </p>
                {base && !base.severidad && !form.severidad && (
                  <p className="text-xs text-red-600 bg-red-50 border border-red-200 rounded-lg px-3 py-2 mb-2">
                    Severidad inválida recibida: "{base.severidad_api ?? 'vacía'}". Elige un nivel antes de guardar.
                  </p>
                )}
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
                  {Object.entries(severidadConfig).map(([key, config]) => (
                    <button
                      key={key}
                      type="button"
                      aria-pressed={form.severidad === key}
                      onClick={() => actualizar('severidad', key)}
                      className={`px-3 py-2 rounded-lg text-sm font-medium border transition-colors ${
                        form.severidad === key ? config.activo : 'bg-white border-gray-200 text-gray-500 hover:bg-gray-50'
                      }`}
                    >
                      {config.label}
                    </button>
                  ))}
                </div>
                {errores.severidad && <p className="text-xs text-red-600 mt-2">{errores.severidad}</p>}
              </div>
            </div>
          </div>

          {/* ==================================================== */}
          {/* AVISOS Y BOTONES DE ACCIÓN */}
          {/* ==================================================== */}
          <div className="flex flex-wrap items-center justify-end gap-3">
            {aviso && (
              <div
                role={aviso.tipo === 'error' ? 'alert' : 'status'}
                className={`flex items-center gap-2 mr-auto px-4 py-2 rounded-lg text-sm ${
                  aviso.tipo === 'exito' ? 'bg-green-50 text-green-700 border border-green-200' : 'bg-red-50 text-red-700 border border-red-200'
                }`}
              >
                {aviso.tipo === 'exito' ? <Check size={16} /> : <AlertTriangle size={16} />}
                {aviso.texto}
              </div>
            )}
            {hayCambios && !aviso && <span className="text-xs text-gray-500 mr-auto">Hay cambios sin guardar</span>}
            <button
              type="button"
              onClick={handleCancelar}
              disabled={!hayCambios || guardando}
              className="px-6 py-2.5 border border-gray-200 rounded-lg text-sm font-medium text-gray-600 hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              Cancelar
            </button>
            <button
              type="button"
              onClick={handleGuardar}
              disabled={!puedeGuardar}
              className="flex items-center gap-2 bg-green-500 hover:bg-green-600 text-white px-6 py-2.5 rounded-lg text-sm font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:bg-green-500"
            >
              <Save size={16} />
              {guardando ? 'Guardando...' : base?.has_rule ? 'Guardar Reglas' : 'Crear Regla'}
            </button>
          </div>
        </fieldset>
      )}
    </div>
  );
};

export default HaccpRulesView;
