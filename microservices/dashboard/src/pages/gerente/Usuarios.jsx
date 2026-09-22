import React, { useState } from 'react';
import { Plus, Pencil, Ban, CheckCircle2 } from 'lucide-react';
import Modal from '../../components/ui/Modal';
import { useFetch } from '../../hooks/useApi';
import { getUsuarios, crearUsuario, actualizarUsuario, desactivarUsuario } from '../../api/usuarios';
import { isValidEmail, isRequired } from '../../utils/validators';

const MOCK_USUARIOS = [
  { id: 1, nombre: 'Alexis Monsalve', email: 'alexis@cryometric.cl', rol: 'gerente', activo: true },
  { id: 2, nombre: 'José Pérez', email: 'jose.tecnico@cryometric.cl', rol: 'tecnico', activo: true },
  { id: 3, nombre: 'Diego Torres', email: 'diego.tecnico@cryometric.cl', rol: 'tecnico', activo: false },
];

const emptyForm = { nombre: '', email: '', rol: 'tecnico' };

// Gestión de Usuarios (SOLO GERENTE) — CU-13.
const Usuarios = () => {
  const { data: usuarios, loading, isFallback, reload } = useFetch(getUsuarios, [], MOCK_USUARIOS);
  const [modalOpen, setModalOpen] = useState(false);
  const [editando, setEditando] = useState(null);
  const [form, setForm] = useState(emptyForm);
  const [errores, setErrores] = useState({});
  const [guardando, setGuardando] = useState(false);

  const abrirNuevo = () => { setEditando(null); setForm(emptyForm); setErrores({}); setModalOpen(true); };
  const abrirEditar = (u) => {
    setEditando(u.id);
    setForm({ nombre: u.nombre, email: u.email, rol: u.rol });
    setErrores({});
    setModalOpen(true);
  };

  const validar = () => {
    const err = {};
    if (!isRequired(form.nombre)) err.nombre = 'El nombre es obligatorio';
    if (!isValidEmail(form.email)) err.email = 'Ingresa un email válido';
    setErrores(err);
    return Object.keys(err).length === 0;
  };

  const guardar = async (e) => {
    e.preventDefault();
    if (!validar()) return;
    setGuardando(true);
    try {
      if (editando) await actualizarUsuario(editando, form);
      else await crearUsuario(form);
    } catch (err) {
      if (err.message?.toLowerCase().includes('registrado')) {
        setErrores({ email: 'El email ya está registrado' });
        setGuardando(false);
        return;
      }
      // El backend puede no estar disponible aún.
    } finally {
      setGuardando(false);
      setModalOpen(false);
      reload();
    }
  };

  const toggleActivo = async (u) => {
    try {
      await desactivarUsuario(u.id, !u.activo);
    } catch (err) {
      // El backend puede no estar disponible aún.
    } finally {
      reload();
    }
  };

  const lista = usuarios || [];

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-800">Gestión de Usuarios</h1>
          <p className="text-sm text-gray-500">Administra las cuentas de gerentes y técnicos</p>
        </div>
        <button onClick={abrirNuevo}
          className="flex items-center gap-2 bg-green-600 hover:bg-green-700 text-white text-sm font-medium px-4 py-2 rounded-lg">
          <Plus size={16} /> Agregar usuario
        </button>
      </div>

      {isFallback && (
        <div className="text-xs text-yellow-600 bg-yellow-50 px-3 py-2 rounded-lg mb-4 inline-block">
          Mostrando datos de ejemplo (sin conexión con la API)
        </div>
      )}

      <div className="bg-white rounded-lg shadow-md overflow-hidden">
        {loading ? (
          <p className="p-6 text-sm text-gray-500">Cargando usuarios...</p>
        ) : (
          <table className="w-full text-sm">
            <thead className="bg-gray-50">
              <tr className="text-left text-gray-500">
                <th className="px-6 py-3 font-medium">Usuario</th>
                <th className="px-6 py-3 font-medium">Email</th>
                <th className="px-6 py-3 font-medium">Rol</th>
                <th className="px-6 py-3 font-medium">Estado</th>
                <th className="px-6 py-3 font-medium">Acciones</th>
              </tr>
            </thead>
            <tbody>
              {lista.map((u) => (
                <tr key={u.id} className="border-t border-gray-100">
                  <td className="px-6 py-3 flex items-center gap-2">
                    <div className="w-8 h-8 rounded-full bg-green-100 text-green-600 flex items-center justify-center text-xs font-semibold">
                      {u.nombre.split(' ').map((n) => n[0]).slice(0, 2).join('')}
                    </div>
                    {u.nombre}
                  </td>
                  <td className="px-6 py-3 text-gray-500">{u.email}</td>
                  <td className="px-6 py-3 capitalize">{u.rol}</td>
                  <td className="px-6 py-3">
                    <span className={`px-2 py-1 rounded-full text-xs ${u.activo ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-500'}`}>
                      {u.activo ? 'Activo' : 'Desactivado'}
                    </span>
                  </td>
                  <td className="px-6 py-3 flex gap-2">
                    <button onClick={() => abrirEditar(u)} className="flex items-center gap-1 text-xs text-gray-600 hover:text-green-600">
                      <Pencil size={14} /> Editar
                    </button>
                    <button onClick={() => toggleActivo(u)}
                      className={`flex items-center gap-1 text-xs ${u.activo ? 'text-red-500 hover:text-red-600' : 'text-green-600 hover:text-green-700'}`}>
                      {u.activo ? <><Ban size={14} /> Desactivar</> : <><CheckCircle2 size={14} /> Activar</>}
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      <Modal isOpen={modalOpen} onClose={() => setModalOpen(false)} title={editando ? 'Editar usuario' : 'Agregar usuario'}>
        <form onSubmit={guardar} className="space-y-4">
          <label className="block text-sm text-gray-600">
            Nombre
            <input value={form.nombre} onChange={(e) => setForm({ ...form, nombre: e.target.value })}
              className="w-full mt-1 border border-gray-200 rounded-lg px-3 py-2 text-sm" />
            {errores.nombre && <p className="text-xs text-red-500 mt-1">{errores.nombre}</p>}
          </label>
          <label className="block text-sm text-gray-600">
            Email
            <input value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })}
              className="w-full mt-1 border border-gray-200 rounded-lg px-3 py-2 text-sm" />
            {errores.email && <p className="text-xs text-red-500 mt-1">{errores.email}</p>}
          </label>
          <label className="block text-sm text-gray-600">
            Rol
            <select value={form.rol} onChange={(e) => setForm({ ...form, rol: e.target.value })}
              className="w-full mt-1 border border-gray-200 rounded-lg px-3 py-2 text-sm">
              <option value="gerente">Gerente</option>
              <option value="tecnico">Técnico</option>
            </select>
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

export default Usuarios;
