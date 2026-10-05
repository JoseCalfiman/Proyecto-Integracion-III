import React, { useState, useEffect } from 'react';
import {
  ThermometerSnowflake, Save, Search, Bell, HelpCircle,
  Download, User, Check, AlertTriangle, Edit2,
} from 'lucide-react';
import { useFetch } from '../../hooks/useApi';
import { getReglasHaccp, actualizarReglasPorCamara } from '../../api/haccp';

// ============================================================
// DATOS MOCK
// ============================================================
const MOCK_CAMARAS = [
  { camara_id: 1, camara: 'Cámara Principal 01 (Carnes)', temp_max: -18, temp_min: -25, tiempo_tolerancia: 15, severidad: 'critico', activa: true },
  { camara_id: 2, camara: 'Cámara Principal 02 (Lácteos)', temp_max: 4, temp_min: -4, tiempo_tolerancia: 30, severidad: 'medio', activa: true },
  { camara_id: 3, camara: 'Cámara Secundaria 01 (Verduras)', temp_max: 6, temp_min: -2, tiempo_tolerancia: 45, severidad: 'bajo', activa: false },
];

const severidadConfig = {
  bajo: { label: 'Bajo', color: 'gray' },
  medio: { label: 'Medio', color: 'blue' },
  critico: { label: 'Crítico', color: 'red' },
};

// ============================================================
// COMPONENTE
// ============================================================
const HaccpRulesView = () => {
  const { data: camaras, loading, isFallback, reload } = useFetch(getReglasHaccp, [], MOCK_CAMARAS);

  const [camaraSeleccionada, setCamaraSeleccionada] = useState(null);
  const [form, setForm] = useState({
    temp_max: -18,
    temp_min: -25,
    tiempo_tolerancia: 15,
    severidad: 'critico',
    activa: true,
  });
  const [guardando, setGuardando] = useState(false);

  const lista = Array.isArray(camaras) ? camaras : [];

  // ============================================================
  // CARGAR LA PRIMERA CÁMARA AL INICIO
  // ============================================================
  useEffect(() => {
    if (lista.length > 0 && !camaraSeleccionada) {
      handleSeleccionarCamara(lista[0]);
    }
  }, [lista]);

  // ============================================================
  // SELECCIONAR CÁMARA
  // ============================================================
  const handleSeleccionarCamara = (camara) => {
    setCamaraSeleccionada(camara);
    setForm({
      temp_max: camara.temp_max,
      temp_min: camara.temp_min,
      tiempo_tolerancia: camara.tiempo_tolerancia,
      severidad: camara.severidad || 'medio',
      activa: camara.activa,
    });
  };

  // ============================================================
  // GUARDAR REGLAS
  // ============================================================
  const handleGuardar = async () => {
    if (!camaraSeleccionada) return;
    setGuardando(true);
    try {
      await actualizarReglasPorCamara(camaraSeleccionada.camara_id, form);
      reload();
    } catch (err) {
      alert('No se pudo guardar. El backend aún no está disponible.');
    } finally {
      setGuardando(false);
    }
  };

  // ============================================================
  // CANCELAR (restaurar valores originales)
  // ============================================================
  const handleCancelar = () => {
    if (camaraSeleccionada) handleSeleccionarCamara(camaraSeleccionada);
  };

  return (
    <div>
      {/* ==================================================== */}
      {/* HEADER SUPERIOR */}
      {/* ==================================================== */}
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold text-gray-800">Configuración Reglas HACCP</h1>
        <div className="flex items-center gap-3">
          <span className="text-xs font-medium px-3 py-1 rounded-full bg-yellow-100 text-yellow-700">
            Acceso Autorizado: Gerente / Técnico
          </span>
          <button className="relative p-2 rounded-full hover:bg-gray-100">
            <Bell size={20} className="text-gray-600" />
            <span className="absolute top-1 right-1 w-2 h-2 bg-red-500 rounded-full"></span>
          </button>
          <button className="p-2 rounded-full hover:bg-gray-100">
            <HelpCircle size={20} className="text-gray-600" />
          </button>
          <button className="flex items-center gap-2 bg-green-500 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-green-600">
            <Download size={16} />
            Descargar Reporte
          </button>
          <div className="w-9 h-9 rounded-full bg-gray-200 flex items-center justify-center">
            <User size={18} className="text-gray-600" />
          </div>
        </div>
      </div>

      {isFallback && (
        <div className="text-xs text-yellow-600 bg-yellow-50 px-3 py-2 rounded-lg mb-4 inline-block">
          Mostrando datos de ejemplo (sin conexión con la API)
        </div>
      )}

      {/* ==================================================== */}
      {/* SELECCIONAR CÁMARA */}
      {/* ==================================================== */}
      <div className="bg-white p-6 rounded-lg shadow-md mb-6">
        <h2 className="text-lg font-semibold text-gray-800 mb-1">Seleccionar Cámara</h2>
        <p className="text-sm text-gray-500 mb-4">
          Elija la cámara frigorífica para configurar los parámetros HACCP de monitoreo continuo.
        </p>
        <select
          value={camaraSeleccionada?.camara_id || ''}
          onChange={(e) => {
            const camara = lista.find((c) => String(c.camara_id) === e.target.value);
            if (camara) handleSeleccionarCamara(camara);
          }}
          className="w-full border border-gray-200 rounded-lg px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-green-500"
        >
          {lista.map((c) => (
            <option key={c.camara_id} value={c.camara_id}>
              {c.camara}
            </option>
          ))}
        </select>

        {/* Switch de Estado */}
        <div className="flex items-center justify-between mt-6 pt-4 border-t border-gray-100">
          <div>
            <p className="font-medium text-gray-700 text-sm">Estado de Reglas HACCP</p>
            <p className="text-xs text-gray-500">
              Activar o desactivar el monitoreo de reglas para esta cámara
            </p>
          </div>
          <div className="flex items-center gap-3">
            <button
              type="button"
              onClick={() => setForm({ ...form, activa: !form.activa })}
              className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
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
        {/* ================================================ */}
        {/* LÍMITES DE TEMPERATURA */}
        {/* ================================================ */}
        <div className="bg-white p-6 rounded-lg shadow-md">
          <div className="flex items-center justify-between mb-6">
            <div className="flex items-center gap-2">
              <ThermometerSnowflake size={20} className="text-green-600" />
              <h2 className="font-semibold text-gray-800">Límites de Temperatura</h2>
            </div>
            <button className="p-1.5 rounded-lg hover:bg-gray-100">
              <Edit2 size={16} className="text-gray-400" />
            </button>
          </div>

          {/* Temperatura Máxima */}
          <div className="mb-6">
            <label className="block text-xs text-gray-500 mb-2">
              Temperatura Máxima Crítica (°C)
            </label>
            <div className="flex items-center gap-4">
              <input
                type="range"
                min="-30"
                max="10"
                step="1"
                value={form.temp_max}
                onChange={(e) => setForm({ ...form, temp_max: parseFloat(e.target.value) })}
                className="flex-1 accent-green-500"
              />
              <div className="w-20 border border-gray-200 rounded-lg px-3 py-1.5 text-sm text-center font-medium">
                {form.temp_max}°C
              </div>
            </div>
            <p className="text-xs text-gray-400 mt-2">
              Límite superior antes de activar alarma HACCP.
            </p>
          </div>

          {/* Temperatura Mínima */}
          <div>
            <label className="block text-xs text-gray-500 mb-2">
              Temperatura Mínima (°C)
            </label>
            <div className="flex items-center gap-4">
              <input
                type="range"
                min="-40"
                max="0"
                step="1"
                value={form.temp_min}
                onChange={(e) => setForm({ ...form, temp_min: parseFloat(e.target.value) })}
                className="flex-1 accent-green-500"
              />
              <div className="w-20 border border-gray-200 rounded-lg px-3 py-1.5 text-sm text-center font-medium">
                {form.temp_min}°C
              </div>
            </div>
            <p className="text-xs text-gray-400 mt-2">
              Límite inferior para optimización de energía.
            </p>
          </div>
        </div>

        {/* ================================================ */}
        {/* REGLAS DE TOLERANCIA */}
        {/* ================================================ */}
        <div className="bg-white p-6 rounded-lg shadow-md">
          <div className="flex items-center justify-between mb-6">
            <div className="flex items-center gap-2">
              <AlertTriangle size={20} className="text-red-500" />
              <h2 className="font-semibold text-gray-800">Reglas de Tolerancia</h2>
            </div>
            <button className="p-1.5 rounded-lg hover:bg-gray-100">
              <Edit2 size={16} className="text-gray-400" />
            </button>
          </div>

          {/* Tiempo de Tolerancia */}
          <div className="mb-6">
            <label className="block text-xs text-gray-500 mb-2">
              Tiempo de Tolerancia (Minutos)
            </label>
            <div className="flex items-center gap-4">
              <input
                type="range"
                min="1"
                max="60"
                step="1"
                value={form.tiempo_tolerancia}
                onChange={(e) => setForm({ ...form, tiempo_tolerancia: parseInt(e.target.value) })}
                className="flex-1 accent-green-500"
              />
              <div className="w-20 border border-gray-200 rounded-lg px-3 py-1.5 text-sm text-center font-medium">
                {form.tiempo_tolerancia}min
              </div>
            </div>
            <p className="text-xs text-gray-400 mt-2">
              Tiempo permitido fuera de rango antes de alertar (ej. ciclos de deshielo).
            </p>
          </div>

          {/* Nivel de Severidad */}
          <div>
            <label className="block text-xs text-gray-500 mb-2">
              Nivel de Severidad de Alarma
            </label>
            <div className="grid grid-cols-3 gap-2">
              {Object.entries(severidadConfig).map(([key, config]) => (
                <button
                  key={key}
                  type="button"
                  onClick={() => setForm({ ...form, severidad: key })}
                  className={`px-3 py-2 rounded-lg text-sm font-medium border transition-colors ${
                    form.severidad === key
                      ? config.color === 'red'
                        ? 'bg-red-50 border-red-300 text-red-700'
                        : config.color === 'blue'
                        ? 'bg-blue-50 border-blue-300 text-blue-700'
                        : 'bg-gray-100 border-gray-300 text-gray-700'
                      : 'bg-white border-gray-200 text-gray-500 hover:bg-gray-50'
                  }`}
                >
                  {config.label}
                </button>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* ==================================================== */}
      {/* BOTONES DE ACCIÓN */}
      {/* ==================================================== */}
      <div className="flex items-center justify-end gap-3">
        <button
          onClick={handleCancelar}
          className="px-6 py-2.5 border border-gray-200 rounded-lg text-sm font-medium text-gray-600 hover:bg-gray-50"
        >
          Cancelar
        </button>
        <button
          onClick={handleGuardar}
          disabled={guardando}
          className="flex items-center gap-2 bg-green-500 hover:bg-green-600 text-white px-6 py-2.5 rounded-lg text-sm font-medium transition-colors"
        >
          <Save size={16} />
          {guardando ? 'Guardando...' : 'Guardar Reglas'}
        </button>
      </div>
    </div>
  );
};

export default HaccpRulesView;