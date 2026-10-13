import React, { useState } from 'react';
import {
  Plus, Search, Bell, HelpCircle, Download, User,
  Camera as CameraIcon, Check, AlertCircle, Filter,
} from 'lucide-react';
import { useFetch } from '../../hooks/useApi';
import { getCamaras, crearCamara, actualizarCamara, eliminarCamara } from '../../api/camaras';

// ============================================================
// DATOS MOCK
// ============================================================
const MOCK_CAMARAS = [
  {
    id: 1,
    nombre: 'Cámara Principal 01',
    ubicacion: 'Sector Norte - Congelados',
    sensor_id: 'SN-1824',
    mcu_id: 'MCU-991',
    setpoint: -18.0,
    estado: 'en_linea',
  },
  {
    id: 2,
    nombre: 'Cámara Auxiliar A',
    ubicacion: 'Sector Sur - Refrigerados',
    sensor_id: 'SN-1088',
    mcu_id: 'MCU-992',
    setpoint: 4.5,
    estado: 'en_linea',
  },
  {
    id: 3,
    nombre: 'Cámara Túnel 03',
    ubicacion: 'Área de Despacho',
    sensor_id: 'SN-2941',
    mcu_id: 'MCU-993',
    setpoint: -22.0,
    estado: 'revision',
  },
];

// ============================================================
// CONFIGURACIÓN DE ESTADOS
// ============================================================
const estadoConfig = {
  en_linea: { label: 'En Línea', color: 'green', icon: Check },
  revision: { label: 'Revisión', color: 'yellow', icon: AlertCircle },
  offline: { label: 'Offline', color: 'gray', icon: AlertCircle },
};

const emptyForm = {
  nombre: '',
  ubicacion: '',
  setpoint: '',
  sensor_id: '',
  modelo_sensor: '',
  ultima_calibracion: '',
  mcu_id: '',
  modelo_firmware: '',
};

// ============================================================
// COMPONENTE
// ============================================================
const Camaras = () => {
  const { data: camaras, loading, isFallback, reload } = useFetch(getCamaras, [], MOCK_CAMARAS);
  const [form, setForm] = useState(emptyForm);
  const [editando, setEditando] = useState(null);
  const [guardando, setGuardando] = useState(false);
  const [busqueda, setBusqueda] = useState('');

  const lista = Array.isArray(camaras) ? camaras : [];

  // ============================================================
  // FILTRAR POR BÚSQUEDA
  // ============================================================
  const listaFiltrada = lista.filter((c) => {
    if (!busqueda) return true;
    const texto = busqueda.toLowerCase();
    return (
      c.nombre?.toLowerCase().includes(texto) ||
      c.ubicacion?.toLowerCase().includes(texto) ||
      c.sensor_id?.toLowerCase().includes(texto)
    );
  });

  // ============================================================
  // GUARDAR (crear o actualizar)
  // ============================================================
  const handleGuardar = async (e) => {
    e.preventDefault();
    setGuardando(true);
    try {
      if (editando) await actualizarCamara(editando, form);
      else await crearCamara(form);
      setForm(emptyForm);
      setEditando(null);
      reload();
    } catch (err) {
      alert('No se pudo guardar. El backend aún no está disponible.');
    } finally {
      setGuardando(false);
    }
  };

  // ============================================================
  // EDITAR
  // datos que no estan en el mer: modelo_sensor, ultima_calibracion, modelo_firmware, mcu_id,
  // agregar dos cempos en lugar de setpoint, son la tempretura minima y maxima. 
  // parte en la base de datos es: operating_max_temp / operating_min_temp
  // ============================================================
  const handleEditar = (c) => {
    setEditando(c.id);
    setForm({
      nombre: c.nombre || '',
      ubicacion: c.ubicacion || '',
      setpoint: c.setpoint || '',
      sensor_id: c.sensor_id || '',
      modelo_sensor: c.modelo_sensor || '',
      ultima_calibracion: c.ultima_calibracion || '',
      mcu_id: c.mcu_id || '',
      modelo_firmware: c.modelo_firmware || '',
    });
  };

  // ============================================================
  // ELIMINAR
  // ============================================================
  const handleEliminar = async (c) => {
    if (!window.confirm(`¿Confirma la eliminación de "${c.nombre}"?`)) return;
    try {
      await eliminarCamara(c.id);
      reload();
    } catch (err) {
      alert('No se pudo eliminar. El backend aún no está disponible.');
    }
  };

  return (
    <div>
      {/* ==================================================== */}
      {/* HEADER SUPERIOR */}
      {/* ==================================================== */}
      <div className="flex items-center justify-between mb-6">
        <div className="relative flex-1 max-w-md">
          <Search size={18} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
          <input
            type="text"
            placeholder="Buscar..."
            value={busqueda}
            onChange={(e) => setBusqueda(e.target.value)}
            className="w-full pl-10 pr-4 py-2 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-green-500"
          />
        </div>
        <div className="flex items-center gap-3">
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

      {/* ==================================================== */}
      {/* TÍTULO */}
      {/* ==================================================== */}
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-800">Gestión de Infraestructura</h1>
        <p className="text-sm text-gray-500">
          Añade, edita o elimina sensores y cámaras de la red de monitoreo.
        </p>
      </div>

      {/* ==================================================== */}
      {/* BANNER DE ACCESO RESTRINGIDO (GERENTE) */}
      {/* ==================================================== */}
      <div className="bg-yellow-50 border border-yellow-200 rounded-lg px-4 py-2 mb-6 inline-flex items-center gap-2">
        <AlertCircle size={16} className="text-yellow-600" />
        <span className="text-sm text-yellow-700 font-medium">
          Acceso restringido: Solo Perfil Gerente
        </span>
      </div>

      {isFallback && (
        <div className="text-xs text-yellow-600 bg-yellow-50 px-3 py-2 rounded-lg mb-4 inline-block">
          Mostrando datos de ejemplo (sin conexión con la API)
        </div>
      )}

      {/* ==================================================== */}
      {/* LAYOUT DE 2 COLUMNAS */}
      {/* ==================================================== */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* ================================================ */}
        {/* FORMULARIO (columna izquierda) */}
        {/* ================================================ */}
        <div className="lg:col-span-1 bg-white p-6 rounded-lg shadow-md h-fit">
          <div className="flex items-center gap-2 mb-4">
            <div className="p-2 bg-green-50 rounded-lg">
              <Plus size={18} className="text-green-600" />
            </div>
            <h2 className="font-semibold text-gray-800">
              {editando ? 'Editar Cámara' : 'Agregar Cámara'}
            </h2>
          </div>

          <form onSubmit={handleGuardar} className="space-y-4">
            {/* Nombre */}
            <div>
              <label className="block text-xs text-gray-500 mb-1">Nombre de la Cámara</label>
              <input
                required
                type="text"
                value={form.nombre}
                onChange={(e) => setForm({ ...form, nombre: e.target.value })}
                placeholder="Ej: Cámara Frigorífica 04"
                className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-green-500"
              />
            </div>

            {/* Ubicación */}
            <div>
              <label className="block text-xs text-gray-500 mb-1">Ubicación</label>
              <select
                value={form.ubicacion}
                onChange={(e) => setForm({ ...form, ubicacion: e.target.value })}
                className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm"
              >
                <option value="">Selecciona sector...</option>
                <option value="Sector Norte - Congelados">Sector Norte - Congelados</option>
                <option value="Sector Sur - Refrigerados">Sector Sur - Refrigerados</option>
                <option value="Área de Despacho">Área de Despacho</option>
              </select>
            </div>

            {/* Setpoint + Sensor ID */}
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-xs text-gray-500 mb-1">Setpoint (°C)</label>
                <input
                  required
                  type="number"
                  step="0.1"
                  value={form.setpoint}
                  onChange={(e) => setForm({ ...form, setpoint: e.target.value })}
                  placeholder="-18.0"
                  className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm"
                />
              </div>
              <div>
                <label className="block text-xs text-gray-500 mb-1">Sensor ID</label>
                <input
                  required
                  type="text"
                  value={form.sensor_id}
                  onChange={(e) => setForm({ ...form, sensor_id: e.target.value })}
                  placeholder="SN-892"
                  className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm"
                />
              </div>
            </div>

            {/* Modelo + Calibración */}
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-xs text-gray-500 mb-1">Modelo Sensor</label>
                <input
                  type="text"
                  value={form.modelo_sensor}
                  onChange={(e) => setForm({ ...form, modelo_sensor: e.target.value })}
                  placeholder="PT100-Ult"
                  className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm"
                />
              </div>
              <div>
                <label className="block text-xs text-gray-500 mb-1">Última Calibración</label>
                <input
                  type="date"
                  value={form.ultima_calibracion}
                  onChange={(e) => setForm({ ...form, ultima_calibracion: e.target.value })}
                  className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm"
                />
              </div>
            </div>

            {/* Microcontrolador */}
            <div className="pt-3 border-t border-gray-100">
              <p className="text-xs font-medium text-gray-700 mb-2">Microcontrolador Asociado</p>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs text-gray-500 mb-1">ID Microcontrolador</label>
                  <input
                    type="text"
                    value={form.mcu_id}
                    onChange={(e) => setForm({ ...form, mcu_id: e.target.value })}
                    placeholder="MCU-772"
                    className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm"
                  />
                </div>
                <div>
                  <label className="block text-xs text-gray-500 mb-1">Modelo / Firmware</label>
                  <input
                    type="text"
                    value={form.modelo_firmware}
                    onChange={(e) => setForm({ ...form, modelo_firmware: e.target.value })}
                    placeholder="ESP32-S3 v2"
                    className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm"
                  />
                </div>
              </div>
            </div>

            {/* Botón Guardar */}
            <button
              type="submit"
              disabled={guardando}
              className="w-full flex items-center justify-center gap-2 bg-green-500 hover:bg-green-600 text-white text-sm font-medium px-4 py-2.5 rounded-lg transition-colors"
            >
              <Check size={16} />
              {guardando ? 'Guardando...' : editando ? 'Actualizar Cambios' : 'Confirmar Cambios'}
            </button>

            {/* Botón Cancelar (si está editando) */}
            {editando && (
              <button
                type="button"
                onClick={() => { setEditando(null); setForm(emptyForm); }}
                className="w-full text-sm text-gray-500 hover:text-gray-700 py-1"
              >
                Cancelar edición
              </button>
            )}
          </form>
        </div>

        {/* ================================================ */}
        {/* TABLA DE CÁMARAS (columna derecha) */}
        {/* ================================================ */}
        <div className="lg:col-span-2 bg-white rounded-lg shadow-md overflow-hidden">
          <div className="flex items-center justify-between px-6 py-4 border-b border-gray-100">
            <div className="flex items-center gap-2">
              <CameraIcon size={18} className="text-green-600" />
              <h2 className="font-semibold text-gray-800">Cámaras Activas</h2>
            </div>
            <button className="p-2 rounded-lg hover:bg-gray-50">
              <Filter size={16} className="text-gray-400" />
            </button>
          </div>

          {loading ? (
            <p className="p-6 text-sm text-gray-500">Cargando cámaras...</p>
          ) : listaFiltrada.length === 0 ? (
            <p className="p-6 text-sm text-gray-500">No hay cámaras registradas.</p>
          ) : (
            <table className="w-full text-sm">
              <thead className="bg-gray-50">
                <tr className="text-left text-gray-500 uppercase text-xs">
                  <th className="px-6 py-3 font-medium">Cámara</th>
                  <th className="px-6 py-3 font-medium">Ubicación</th>
                  <th className="px-6 py-3 font-medium">Sensor ID</th>
                  <th className="px-6 py-3 font-medium">MCU ID</th>
                  <th className="px-6 py-3 font-medium">Setpoint</th>
                  <th className="px-6 py-3 font-medium">Estado</th>
                  <th className="px-6 py-3 font-medium">Acciones</th>
                </tr>
              </thead>
              <tbody>
                {listaFiltrada.map((c) => {
                  const est = estadoConfig[c.estado] || estadoConfig.offline;
                  const IconEst = est.icon;

                  return (
                    <tr
                      key={c.id}
                      className={`border-t border-gray-100 hover:bg-gray-50 ${
                        c.estado === 'revision' ? 'bg-yellow-50/30' : ''
                      }`}
                    >
                      <td className="px-6 py-3 font-medium text-gray-800">{c.nombre}</td>
                      <td className="px-6 py-3 text-gray-600">{c.ubicacion}</td>
                      <td className="px-6 py-3 font-mono text-xs text-gray-500">{c.sensor_id}</td>
                      <td className="px-6 py-3 font-mono text-xs text-gray-500">{c.mcu_id}</td>
                      <td className="px-6 py-3 font-medium text-gray-800">{c.setpoint} °C</td>
                      <td className="px-6 py-3">
                        <span
                          className={`inline-flex items-center gap-1 text-xs font-medium px-2 py-1 rounded-full ${
                            est.color === 'green'
                              ? 'bg-green-100 text-green-700'
                              : est.color === 'yellow'
                              ? 'bg-yellow-100 text-yellow-700'
                              : 'bg-gray-100 text-gray-600'
                          }`}
                        >
                          <IconEst size={12} />
                          {est.label}
                        </span>
                      </td>
                      <td className="px-6 py-3">
                        <div className="flex gap-2">
                          <button
                            onClick={() => handleEditar(c)}
                            className="text-xs text-gray-600 hover:text-green-600"
                            title="Editar"
                          >
                            ✏️
                          </button>
                          <button
                            onClick={() => handleEliminar(c)}
                            className="text-xs text-red-500 hover:text-red-600"
                            title="Eliminar"
                          >
                            🗑️
                          </button>
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          )}

          {/* Footer con contador */}
          <div className="flex items-center justify-between px-6 py-3 border-t border-gray-100 text-xs text-gray-500">
            <span>
              Mostrando {listaFiltrada.length} de {lista.length} cámaras
            </span>
            <div className="flex gap-2">
              <button className="p-1 rounded hover:bg-gray-100 disabled:opacity-50" disabled>←</button>
              <button className="p-1 rounded hover:bg-gray-100 disabled:opacity-50" disabled>→</button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Camaras;