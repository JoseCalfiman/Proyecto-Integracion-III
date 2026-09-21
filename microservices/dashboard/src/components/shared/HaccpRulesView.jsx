import React, { useState } from 'react';
import { Settings, Save, ThermometerSnowflake } from 'lucide-react';
import { useFetch } from '../../hooks/useApi';
import { getReglasHaccp, actualizarReglasPorCamara } from '../../api/haccp';

const MOCK_REGLAS = [
  { camara_id: 1, camara: 'Cámara Principal 01', temp_max: 4, temp_min: -5, tiempo_tolerancia: 40, activa: true },
  { camara_id: 2, camara: 'Cámara Principal 02', temp_max: 4, temp_min: -4, tiempo_tolerancia: 30, activa: true },
  { camara_id: 3, camara: 'Cámara Secundaria 01', temp_max: 6, temp_min: -2, tiempo_tolerancia: 45, activa: false },
];

// Reglas HACCP por cámara (CU-12). Gerente y Técnico pueden editar los
// umbrales (temp_max, temp_min, tiempo_tolerancia).
const HaccpRulesView = () => {
  const { data: reglas, loading, isFallback, reload } = useFetch(getReglasHaccp, [], MOCK_REGLAS);
  const [editando, setEditando] = useState(null);
  const [form, setForm] = useState({});
  const [guardando, setGuardando] = useState(false);

  const empezarEdicion = (regla) => {
    setEditando(regla.camara_id);
    setForm({ temp_max: regla.temp_max, temp_min: regla.temp_min, tiempo_tolerancia: regla.tiempo_tolerancia });
  };

  const guardar = async (camaraId) => {
    setGuardando(true);
    try {
      await actualizarReglasPorCamara(camaraId, form);
    } catch (err) {
      // El backend puede no estar disponible aún.
    } finally {
      setEditando(null);
      setGuardando(false);
      reload();
    }
  };

  const lista = reglas || [];

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-800">Reglas HACCP</h1>
          <p className="text-sm text-gray-500">Umbrales de temperatura y tolerancia por cámara</p>
        </div>
        {isFallback && (
          <span className="text-xs text-yellow-600 bg-yellow-50 px-3 py-1 rounded-full">
            Mostrando datos de ejemplo (sin conexión con la API)
          </span>
        )}
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {loading ? (
          <p className="text-sm text-gray-500">Cargando reglas...</p>
        ) : (
          lista.map((r) => (
            <div key={r.camara_id} className="bg-white p-6 rounded-lg shadow-md">
              <div className="flex items-center justify-between mb-4">
                <div className="flex items-center gap-2 font-semibold text-gray-700">
                  <ThermometerSnowflake size={18} className="text-green-600" />
                  {r.camara}
                </div>
                <span className={`text-xs px-2 py-1 rounded-full ${r.activa ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-500'}`}>
                  {r.activa ? 'Activa' : 'Inactiva'}
                </span>
              </div>

              {editando === r.camara_id ? (
                <div className="space-y-3">
                  <label className="block text-xs text-gray-500">
                    Temp. máxima (°C)
                    <input type="number" value={form.temp_max}
                      onChange={(e) => setForm({ ...form, temp_max: e.target.value })}
                      className="w-full mt-1 border border-gray-200 rounded-lg px-3 py-1.5 text-sm" />
                  </label>
                  <label className="block text-xs text-gray-500">
                    Temp. mínima (°C)
                    <input type="number" value={form.temp_min}
                      onChange={(e) => setForm({ ...form, temp_min: e.target.value })}
                      className="w-full mt-1 border border-gray-200 rounded-lg px-3 py-1.5 text-sm" />
                  </label>
                  <label className="block text-xs text-gray-500">
                    Tiempo de tolerancia (min)
                    <input type="number" value={form.tiempo_tolerancia}
                      onChange={(e) => setForm({ ...form, tiempo_tolerancia: e.target.value })}
                      className="w-full mt-1 border border-gray-200 rounded-lg px-3 py-1.5 text-sm" />
                  </label>
                  <div className="flex gap-2 pt-2">
                    <button disabled={guardando} onClick={() => guardar(r.camara_id)}
                      className="flex items-center gap-1 text-xs bg-green-600 text-white px-3 py-1.5 rounded-lg hover:bg-green-700">
                      <Save size={14} /> Guardar
                    </button>
                    <button onClick={() => setEditando(null)}
                      className="text-xs px-3 py-1.5 rounded-lg text-gray-500 hover:bg-gray-50">
                      Cancelar
                    </button>
                  </div>
                </div>
              ) : (
                <div className="space-y-2 text-sm text-gray-600">
                  <div className="flex justify-between"><span>Temp. máxima</span><span className="font-medium text-gray-800">{r.temp_max}°C</span></div>
                  <div className="flex justify-between"><span>Temp. mínima</span><span className="font-medium text-gray-800">{r.temp_min}°C</span></div>
                  <div className="flex justify-between"><span>Tolerancia</span><span className="font-medium text-gray-800">{r.tiempo_tolerancia} min</span></div>
                  <button onClick={() => empezarEdicion(r)}
                    className="flex items-center gap-1 text-xs text-green-600 hover:text-green-700 pt-2">
                    <Settings size={14} /> Editar umbrales
                  </button>
                </div>
              )}
            </div>
          ))
        )}
      </div>
    </div>
  );
};

export default HaccpRulesView;
