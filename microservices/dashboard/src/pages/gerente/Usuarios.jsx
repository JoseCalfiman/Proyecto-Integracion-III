import React, { useState } from 'react';
import {
  Plus, Pencil, Ban, CheckCircle2, Eye, EyeOff, Search,
  User as UserIcon, Bell, HelpCircle, Download,
} from 'lucide-react';
import { useFetch } from '../../hooks/useApi';
import { getUsuarios, crearUsuario, actualizarUsuario, desactivarUsuario } from '../../api/usuarios';
import { isValidEmail, isRequired } from '../../utils/validators';

// ============================================================
// DATOS MOCK
// ============================================================
const MOCK_USUARIOS = [
  { id: 1, nombre: 'Carlos Ramírez', email: 'c.ramirez@cryometric.com', rol: 'gerente', activo: true },
  { id: 2, nombre: 'Lucía Fernández', email: 'l.fernandez@cryometric.com', rol: 'tecnico', activo: false },
  { id: 3, nombre: 'Miguel Ángel Torres', email: 'm.torres@cryometric.com', rol: 'tecnico', activo: true },
];

const emptyForm = { nombre: '', email: '', password: '', rol: 'tecnico' };

// ============================================================
// CONFIGURACIÓN DE COLORES POR ROL
// ============================================================
const rolConfig = {
  gerente: { label: 'Gerente', color: 'blue' },
  tecnico: { label: 'Técnico', color: 'gray' },
};

// ============================================================
// COMPONENTE
// ============================================================
const Usuarios = () => {
  const { data: usuarios, loading, isFallback, reload } = useFetch(getUsuarios, [], MOCK_USUARIOS);
  const [form, setForm] = useState(emptyForm);
  const [editando, setEditando] = useState(null);
  const [errores, setErrores] = useState({});
  const [guardando, setGuardando] = useState(false);
  const [mostrarPassword, setMostrarPassword] = useState(false);
  const [busqueda, setBusqueda] = useState('');

  const lista = Array.isArray(usuarios) ? usuarios : [];

  // ============================================================
  // FILTRO DE BÚSQUEDA
  // ============================================================
  const listaFiltrada = lista.filter((u) => {
    if (!busqueda) return true;
    const texto = busqueda.toLowerCase();
    return (
      u.nombre?.toLowerCase().includes(texto) ||
      u.email?.toLowerCase().includes(texto)
    );
  });

  // ============================================================
  // VALIDACIONES
  // ============================================================
  const validar = () => {
    const err = {};
    if (!isRequired(form.nombre)) err.nombre = 'El nombre es obligatorio';
    if (!isValidEmail(form.email)) err.email = 'Ingresa un email válido';
    if (!editando && !isRequired(form.password)) err.password = 'La contraseña es obligatoria';
    setErrores(err);
    return Object.keys(err).length === 0;
  };

  // ============================================================
  // GUARDAR
  // ============================================================
  const handleGuardar = async (e) => {
    e.preventDefault();
    if (!validar()) return;
    setGuardando(true);
    try {
      if (editando) await actualizarUsuario(editando, form);
      else await crearUsuario(form);
      setForm(emptyForm);
      setEditando(null);
      setErrores({});
      reload();
    } catch (err) {
      if (err.message?.toLowerCase().includes('registrado')) {
        setErrores({ email: 'El email ya está registrado' });
      } else {
        alert('No se pudo guardar. El backend aún no está disponible.');
      }
    } finally {
      setGuardando(false);
    }
  };

  // ============================================================
  // EDITAR
  // ============================================================
  const handleEditar = (u) => {
    setEditando(u.id);
    setForm({ nombre: u.nombre, email: u.email, password: '', rol: u.rol });
    setErrores({});
  };

  // ============================================================
  // ACTIVAR / DESACTIVAR
  // ============================================================
  const handleToggleActivo = async (u) => {
    try {
      await desactivarUsuario(u.id, !u.activo);
      reload();
    } catch (err) {
      alert('No se pudo cambiar el estado. El backend aún no está disponible.');
    }
  };

  return (
    <div>
      {/* ==================================================== */}
      {/* HEADER SUPERIOR */}
      {/* ==================================================== */}
      <div className="flex items-center justify-end gap-3 mb-6">
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
          <UserIcon size={18} className="text-gray-600" />
        </div>
      </div>

      {/* ==================================================== */}
      {/* TÍTULO */}
      {/* ==================================================== */}
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-800">Gestión de Usuarios</h1>
        <p className="text-sm text-gray-500">
          Administración de accesos y roles del personal de planta.
        </p>
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
          <div className="flex items-center gap-2 mb-6">
            <div className="p-2 bg-green-50 rounded-lg">
              <Plus size={18} className="text-green-600" />
            </div>
            <h2 className="font-semibold text-gray-800">
              {editando ? 'Editar Usuario' : 'Nuevo Usuario'}
            </h2>
          </div>

          <form onSubmit={handleGuardar} className="space-y-4">
            {/* Nombre */}
            <div>
              <label className="block text-xs text-gray-500 mb-1">Nombre Completo</label>
              <input
                type="text"
                value={form.nombre}
                onChange={(e) => setForm({ ...form, nombre: e.target.value })}
                placeholder="Ej: Ana Martínez"
                className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-green-500"
              />
              {errores.nombre && <p className="text-xs text-red-500 mt-1">{errores.nombre}</p>}
            </div>

            {/* Email */}
            <div>
              <label className="block text-xs text-gray-500 mb-1">Correo Electrónico</label>
              <input
                type="email"
                value={form.email}
                onChange={(e) => setForm({ ...form, email: e.target.value })}
                placeholder="ana@empresa.com"
                className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-green-500"
              />
              {errores.email && <p className="text-xs text-red-500 mt-1">{errores.email}</p>}
            </div>

            {/* Contraseña Temporal */}
            <div>
              <label className="block text-xs text-gray-500 mb-1">Contraseña Temporal</label>
              <div className="relative">
                <input
                  type={mostrarPassword ? 'text' : 'password'}
                  value={form.password}
                  onChange={(e) => setForm({ ...form, password: e.target.value })}
                  placeholder="••••••••"
                  className="w-full border border-gray-200 rounded-lg px-3 py-2 pr-10 text-sm focus:outline-none focus:ring-2 focus:ring-green-500"
                />
                <button
                  type="button"
                  onClick={() => setMostrarPassword(!mostrarPassword)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"
                >
                  {mostrarPassword ? <EyeOff size={16} /> : <Eye size={16} />}
                </button>
              </div>
              {errores.password && <p className="text-xs text-red-500 mt-1">{errores.password}</p>}
            </div>

            {/* Rol */}
            <div>
              <label className="block text-xs text-gray-500 mb-1">Rol Asignado</label>
              <select
                value={form.rol}
                onChange={(e) => setForm({ ...form, rol: e.target.value })}
                className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm"
              >
                <option value="tecnico">Técnico</option>
                <option value="gerente">Gerente</option>
              </select>
            </div>

            {/* Botón */}
            <button
              type="submit"
              disabled={guardando}
              className="w-full flex items-center justify-center gap-2 bg-green-500 hover:bg-green-600 text-white text-sm font-medium px-4 py-2.5 rounded-lg transition-colors"
            >
              <Plus size={16} />
              {guardando ? 'Guardando...' : editando ? 'Actualizar Usuario' : 'Registrar Usuario'}
            </button>

            {/* Cancelar (si edita) */}
            {editando && (
              <button
                type="button"
                onClick={() => { setEditando(null); setForm(emptyForm); setErrores({}); }}
                className="w-full text-sm text-gray-500 hover:text-gray-700 py-1"
              >
                Cancelar edición
              </button>
            )}
          </form>
        </div>

        {/* ================================================ */}
        {/* TABLA DE USUARIOS (columna derecha) */}
        {/* ================================================ */}
        <div className="lg:col-span-2 bg-white rounded-lg shadow-md overflow-hidden">
          <div className="flex items-center justify-between px-6 py-4 border-b border-gray-100">
            <h2 className="font-semibold text-gray-800">Directorio de Personal</h2>
            <div className="relative">
              <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
              <input
                type="text"
                placeholder="Buscar usuario..."
                value={busqueda}
                onChange={(e) => setBusqueda(e.target.value)}
                className="pl-9 pr-4 py-2 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-green-500 w-64"
              />
            </div>
          </div>

          {loading ? (
            <p className="p-6 text-sm text-gray-500">Cargando usuarios...</p>
          ) : listaFiltrada.length === 0 ? (
            <p className="p-6 text-sm text-gray-500">No hay usuarios registrados.</p>
          ) : (
            <table className="w-full text-sm">
              <thead className="bg-gray-50">
                <tr className="text-left text-gray-500 uppercase text-xs">
                  <th className="px-6 py-3 font-medium">Usuario</th>
                  <th className="px-6 py-3 font-medium">Rol</th>
                  <th className="px-6 py-3 font-medium">Estado</th>
                  <th className="px-6 py-3 font-medium">Acciones</th>
                </tr>
              </thead>
              <tbody>
                {listaFiltrada.map((u) => {
                  const rol = rolConfig[u.rol] || rolConfig.tecnico;

                  return (
                    <tr key={u.id} className="border-t border-gray-100 hover:bg-gray-50">
                      <td className="px-6 py-3">
                        <div className="flex items-center gap-3">
                          <div className="w-9 h-9 rounded-full bg-green-100 text-green-600 flex items-center justify-center text-xs font-semibold">
                            {u.nombre.split(' ').map((n) => n[0]).slice(0, 2).join('')}
                          </div>
                          <div>
                            <p className="font-medium text-gray-800">{u.nombre}</p>
                            <p className="text-xs text-gray-500">{u.email}</p>
                          </div>
                        </div>
                      </td>
                      <td className="px-6 py-3">
                        <span
                          className={`text-xs font-medium px-2 py-1 rounded ${
                            rol.color === 'blue'
                              ? 'text-blue-700 bg-blue-50'
                              : 'text-gray-700 bg-gray-100'
                          }`}
                        >
                          {rol.label}
                        </span>
                      </td>
                      <td className="px-6 py-3">
                        <span className="inline-flex items-center gap-1 text-xs font-medium text-gray-700">
                          <span
                            className={`w-2 h-2 rounded-full ${
                              u.activo ? 'bg-green-500' : 'bg-gray-400'
                            }`}
                          ></span>
                          {u.activo ? 'Activo' : 'Inactivo'}
                        </span>
                      </td>
                      <td className="px-6 py-3">
                        <div className="flex gap-2">
                          <button
                            onClick={() => handleEditar(u)}
                            className="p-1.5 rounded-lg hover:bg-gray-100 text-gray-600"
                            title="Editar"
                          >
                            <Pencil size={14} />
                          </button>
                          <button
                            onClick={() => handleToggleActivo(u)}
                            className={`p-1.5 rounded-lg hover:bg-gray-100 ${
                              u.activo ? 'text-red-500' : 'text-green-600'
                            }`}
                            title={u.activo ? 'Desactivar' : 'Activar'}
                          >
                            {u.activo ? <Ban size={14} /> : <CheckCircle2 size={14} />}
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
              Mostrando {listaFiltrada.length} de {lista.length} usuarios
            </span>
            <div className="flex gap-2">
              <button className="p-1 rounded hover:bg-gray-100 disabled:opacity-50" disabled>←</button>
              <button className="p-1 rounded hover:bg-gray-100 disabled:opacity-50" disabled>→</button>
            </div>
          </div>
        </div>
      </div>

      {/* ==================================================== */}
      {/* NOTA INFORMATIVA */}
      {/* ==================================================== */}
      <div className="mt-6 bg-blue-50 border border-blue-200 rounded-lg px-4 py-3">
        <p className="text-xs text-blue-700">
          <strong>Nota:</strong> El Gerente es quien administra las contraseñas de los técnicos.
        </p>
      </div>
    </div>
  );
};

export default Usuarios;