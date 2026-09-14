import React, { useState } from 'react';
import { Plus, Pencil, Trash2, Camera as CameraIcon } from 'lucide-react';
import Modal from '../../components/ui/Modal';
import { useFetch } from '../../hooks/useApi';
import { getCamaras, crearCamara, actualizarCamara, eliminarCamara } from '../../api/camaras';

const MOCK_CAMARAS = [
  { id: 1, nombre: 'Cámara Principal 01', temp_min: -5, temp_max: 4, sensor: 'Sensor Temp 01' },
  { id: 2, nombre: 'Cámara Principal 02', temp_min: -4, temp_max: 4, sensor: 'Sensor Temp 02' },
  { id: 3, nombre: 'Cámara Secundaria 01', temp_min: -2, temp_max: 6, sensor: 'Sensor Temp 03' },
];

const emptyForm = { nombre: '', temp_min: '', temp_max: '', sensor: '' };

// Configuración de Cámaras (SOLO GERENTE) — CU-11.
const Camaras = () => {
  const { data: camaras, loading, isFallback, reload } = useFetch(getCamaras, [], MOCK_CAMARAS);
  const [modalOpen, setModalOpen] = useState(false);
  const [editando, setEditando] = useState(null);
  const [form, setForm] = useState(emptyForm);
  const [guardando, setGuardando] = useState(false);

  const abrirNueva = () => { setEditando(null); setForm(emptyForm); setModalOpen(true); };
  const abrirEditar = (c) => {
    setEditando(c.id);
    setForm({ nombre: c.nombre, temp_min: c.temp_min, temp_max: c.temp_max, sensor: c.sensor });
    setModalOpen(true);
  };

  const guardar = async (e) => {
    e.preventDefault();
    setGuardando(true);
    try {
      if (editando) await actualizarCamara(editando, form);
      else await crearCamara(form);
    } catch (err) {
      // El backend puede no estar disponible aún.
    } finally {
      setGuardando(false);
      setModalOpen(false);
      reload();
    }
  };

  const eliminar = async (c) => {
    if (!window.confirm(`Esta cámara puede tener datos históricos. ¿Confirma la eliminación de "${c.nombre}"?`)) return;
    try {
      await eliminarCamara(c.id);
    } catch (err) {
      // El backend puede no estar disponible aún.
    } finally {
      reload();
    }
  };

  const lista = camaras || [];

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-800">Configuración de Cámaras</h1>
          <p className="text-sm text-gray-500">Gestiona las cámaras frigoríficas y sus sensores asociados</p>
        </div>
        <button onClick={abrirNueva}
          className="flex items-center gap-2 bg-green-600 hover:bg-green-700 text-white text-sm font-medium px-4 py-2 rounded-lg">
          <Plus size={16} /> Agregar cámara
        </button>
      </div>

      {isFallback && (
        <div className="text-xs text-yellow-600 bg-yellow-50 px-3 py-2 rounded-lg mb-4 inline-block">
          Mostrando datos de ejemplo (sin conexión con la API)
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {loading ? (
          <p className="text-sm text-gray-500">Cargando cámaras...</p>
        ) : (
          lista.map((c) => (
            <div key={c.id} className="bg-white p-6 rounded-lg shadow-md">
              <div className="flex items-center gap-2 font-semibold text-gray-700 mb-3">
                <CameraIcon size={18} className="text-green-600" /> {c.nombre}
              </div>
              <div className="text-sm text-gray-600 space-y-1">
                <div className="flex justify-between"><span>Rango de temperatura</span><span className="font-medium text-gray-800">{c.temp_min}°C a {c.temp_max}°C</span></div>
                <div className="flex justify-between"><span>Sensor asociado</span><span className="font-medium text-gray-800">{c.sensor}</span></div>
              </div>
              <div className="flex gap-2 mt-4 pt-4 border-t border-gray-100">
                <button onClick={() => abrirEditar(c)} className="flex items-center gap-1 text-xs text-gray-600 hover:text-green-600">
                  <Pencil size={14} /> Editar
                </button>
                <button onClick={() => eliminar(c)} className="flex items-center gap-1 text-xs text-red-500 hover:text-red-600">
                  <Trash2 size={14} /> Eliminar
                </button>
              </div>
            </div>
          ))
        )}
      </div>

      <Modal isOpen={modalOpen} onClose={() => setModalOpen(false)} title={editando ? 'Editar cámara' : 'Agregar cámara'}>
        <form onSubmit={guardar} className="space-y-4">
          <label className="block text-sm text-gray-600">
            Nombre
            <input required value={form.nombre} onChange={(e) => setForm({ ...form, nombre: e.target.value })}
              className="w-full mt-1 border border-gray-200 rounded-lg px-3 py-2 text-sm" />
          </label>
          <div className="grid grid-cols-2 gap-3">
            <label className="block text-sm text-gray-600">
              Temp. mínima
              <input required type="number" value={form.temp_min} onChange={(e) => setForm({ ...form, temp_min: e.target.value })}
                className="w-full mt-1 border border-gray-200 rounded-lg px-3 py-2 text-sm" />
            </label>
            <label className="block text-sm text-gray-600">
              Temp. máxima
              <input required type="number" value={form.temp_max} onChange={(e) => setForm({ ...form, temp_max: e.target.value })}
                className="w-full mt-1 border border-gray-200 rounded-lg px-3 py-2 text-sm" />
            </label>
          </div>
          <label className="block text-sm text-gray-600">
            Sensor asociado
            <input required value={form.sensor} onChange={(e) => setForm({ ...form, sensor: e.target.value })}
              className="w-full mt-1 border border-gray-200 rounded-lg px-3 py-2 text-sm" />
          </label>
          <div className="flex justify-end gap-2 pt-2">
            <button type="button" onClick={() => setModalOpen(false)} className="text-sm px-4 py-2 rounded-lg text-gray-500 hover:bg-gray-50">
              Cancelar
            </button>
            <button type="submit" disabled={guardando} className="text-sm px-4 py-2 rounded-lg bg-green-600 text-white hover:bg-green-700">
              {guardando ? 'Guardando...' : 'Guardar'}
            </button>
          </div>
        </form>
      </Modal>
    </div>
  );
};

export default Camaras;
