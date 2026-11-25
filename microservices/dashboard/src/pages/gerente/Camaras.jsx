import { useRef, useState } from 'react';
import { Plus, Search, Camera, Check, AlertCircle, Pencil, Trash2, RefreshCw, X } from 'lucide-react';
import { useFetch } from '../../hooks/useApi';
import { getCamaras, crearCamara, actualizarCamara, eliminarCamara } from '../../api/camaras';

const emptyForm = { nombre: '', ubicacion: '', active: true };
const getTodas = () => getCamaras(true);
const inputClass = 'w-full rounded-lg border border-gray-200 px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-green-500 disabled:bg-gray-50';

const Camaras = () => {
  const { data, loading, error, reload } = useFetch(getTodas, [], null);
  const nombreRef = useRef(null);
  const [form, setForm] = useState(emptyForm);
  const [editando, setEditando] = useState(null);
  const [busy, setBusy] = useState(false);
  const [busqueda, setBusqueda] = useState('');
  const [filtro, setFiltro] = useState('activas');
  const [mensaje, setMensaje] = useState('');
  const [errorAccion, setErrorAccion] = useState('');
  const [porEliminar, setPorEliminar] = useState(null);

  const lista = Array.isArray(data) ? data : [];
  const activas = lista.filter((c) => c.active).length;
  const texto = busqueda.trim().toLowerCase();
  const visibles = lista.filter((c) => {
    const coincideEstado = filtro === 'todas' || (filtro === 'activas' ? c.active : !c.active);
    return coincideEstado && [c.nombre, c.ubicacion, c.id].some((v) => String(v ?? '').toLowerCase().includes(texto));
  });
  const bloqueado = busy || loading || Boolean(error);

  const resetForm = () => { setEditando(null); setForm(emptyForm); };

  const handleNueva = () => {
    resetForm();
    setMensaje('');
    setErrorAccion('');
    nombreRef.current?.focus();
    nombreRef.current?.scrollIntoView({ behavior: 'smooth', block: 'center' });
  };

  const handleGuardar = async (e) => {
    e.preventDefault();
    if (bloqueado) return;
    setMensaje('');
    setErrorAccion('');
    const nombre = form.nombre.trim();
    if (!nombre) { setErrorAccion('Ingresa un nombre válido para la cámara.'); return; }
    setBusy(true);
    try {
      const payload = { nombre, ubicacion: form.ubicacion.trim() };
      if (editando) {
        await actualizarCamara(editando.id, { ...payload, active: form.active });
        setMensaje('Cámara actualizada correctamente.');
        if (filtro === 'activas' && !form.active) setFiltro('todas');
        if (filtro === 'inactivas' && form.active) setFiltro('todas');
      } else {
        const creada = await crearCamara(payload);
        setMensaje(`Cámara registrada correctamente. ID: ${creada.id}`);
        setFiltro('activas');
        setBusqueda('');
      }
      resetForm();
      await reload();
    } catch (err) {
      setErrorAccion(err.message || 'No se pudo guardar la cámara.');
    } finally { setBusy(false); }
  };

  const handleEditar = (c) => {
    setEditando(c);
    setForm({ nombre: c.nombre ?? '', ubicacion: c.ubicacion ?? '', active: c.active });
    setMensaje('');
    setErrorAccion('');
  };

  const handleEliminar = async () => {
    if (!porEliminar || bloqueado) return;
    setBusy(true);
    setMensaje('');
    setErrorAccion('');
    try {
      await eliminarCamara(porEliminar.id, true);
      if (editando?.id === porEliminar.id) resetForm();
      setPorEliminar(null);
      await reload();
      const actualizadas = await getTodas();
      if (actualizadas.some((c) => c.id === porEliminar.id)) {
        throw new Error('La cámara sigue registrada. Comprueba que Ingesta esté actualizado: la versión anterior solo desactiva las cámaras.');
      }
      setMensaje('Cámara eliminada definitivamente.');
    } catch (err) {
      setPorEliminar(null);
      setErrorAccion(err.message || 'No se pudo eliminar la cámara.');
    } finally { setBusy(false); }
  };

  return (
    <div className="space-y-6">
      <header className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold text-gray-800">Gestión de Infraestructura</h1>
          <p className="mt-1 text-sm text-gray-500">Registra, edita y elimina cámaras de la red de monitoreo.</p>
        </div>
        <div className="flex flex-wrap gap-2">
        <button type="button" disabled={bloqueado} onClick={handleNueva} className="inline-flex items-center gap-2 rounded-lg bg-green-600 px-3 py-2 text-sm font-medium text-white hover:bg-green-700 disabled:opacity-50">
          <Plus size={16} /> Nueva cámara
        </button>
        <button type="button" disabled={busy || loading} onClick={reload} className="inline-flex items-center gap-2 rounded-lg border border-gray-200 bg-white px-3 py-2 text-sm text-gray-700 hover:bg-gray-50 disabled:opacity-50">
          <RefreshCw size={16} /> Actualizar lista
        </button>
        </div>
      </header>
      <div className="inline-flex items-center gap-2 rounded-lg border border-yellow-200 bg-yellow-50 px-3 py-2 text-sm text-yellow-700">
        <AlertCircle size={16} /> Acceso restringido: Solo Perfil Gerente
      </div>
      {mensaje && <p role="status" className="rounded-lg border border-green-200 bg-green-50 p-3 text-sm text-green-800">{mensaje}</p>}
      {(error || errorAccion) && <div role="alert" className="rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-700">{errorAccion && <p>{errorAccion}</p>}{error && <p>{error}. Actualiza la lista antes de realizar cambios.</p>}</div>}
      <div className="grid grid-cols-1 gap-6 xl:grid-cols-3">
        <section className="h-fit rounded-xl bg-white p-5 shadow-md">
          <div className="mb-4 flex items-center gap-2">
            <div className="rounded-lg bg-green-50 p-2 text-green-600">{editando ? <Pencil size={18} /> : <Plus size={18} />}</div>
            <h2 className="font-semibold text-gray-800">{editando ? 'Editar cámara' : 'Agregar cámara'}</h2>
          </div>
          <form onSubmit={handleGuardar} className="space-y-4">
            {editando && <div className="rounded-lg bg-gray-50 p-3"><p className="text-xs text-gray-500">ID de cámara (no editable)</p><p className="mt-1 break-all font-mono text-xs text-gray-700">{editando.id}</p></div>}
            <label className="block text-sm text-gray-700">Nombre de la cámara
              <input ref={nombreRef} required maxLength={100} disabled={bloqueado} className={`${inputClass} mt-1`} value={form.nombre} onChange={(e) => setForm({ ...form, nombre: e.target.value })} placeholder="Cámara Principal 05" />
            </label>
            <label className="block text-sm text-gray-700">Ubicación
              <input maxLength={200} disabled={bloqueado} className={`${inputClass} mt-1`} value={form.ubicacion} onChange={(e) => setForm({ ...form, ubicacion: e.target.value })} placeholder="Ej.: Sector Norte - Congelados" />
            </label>
            {editando && <label className="block text-sm text-gray-700">Estado administrativo
              <select disabled={bloqueado} className={`${inputClass} mt-1`} value={form.active ? 'active' : 'inactive'} onChange={(e) => setForm({ ...form, active: e.target.value === 'active' })}>
                <option value="active">Activa</option><option value="inactive">Inactiva</option>
              </select>
              <span className="mt-1 block text-xs text-gray-500">Desactivar conserva el historial y permite reactivar la cámara.</span>
            </label>}
            <button type="submit" disabled={bloqueado} className="flex w-full items-center justify-center gap-2 rounded-lg bg-green-600 px-4 py-2.5 text-sm font-medium text-white hover:bg-green-700 disabled:opacity-50">
              <Check size={16} /> {busy ? 'Procesando...' : editando ? 'Guardar cambios' : 'Crear cámara'}
            </button>
            {editando && <button type="button" disabled={busy} onClick={resetForm} className="w-full py-1 text-sm text-gray-600 hover:text-gray-900 disabled:opacity-50">Cancelar edición</button>}
          </form>
          {!editando && <p className="mt-3 text-xs text-gray-500">Se registrará como activa en tu empresa y recibirá un UUID automático.</p>}
          <p className="mt-4 border-t border-gray-100 pt-3 text-xs text-gray-500">Los sensores y límites térmicos no se modifican con este formulario de cámaras.</p>
        </section>
        <section className="min-w-0 rounded-xl bg-white shadow-md xl:col-span-2">
          <div className="space-y-4 border-b border-gray-100 p-5">
            <div className="flex items-center gap-2"><Camera size={20} className="text-green-600" /><h2 className="font-semibold text-gray-800">{filtro === 'activas' ? 'Cámaras activas' : filtro === 'inactivas' ? 'Cámaras inactivas' : 'Todas las cámaras'}</h2></div>
            {!error && !loading && <p className="text-xs text-gray-500">{activas} activas · {lista.length - activas} inactivas · {lista.length} registradas</p>}
            <div className="flex flex-wrap gap-2">
              <label className="relative min-w-0 flex-1"><Search size={16} className="absolute left-3 top-3 text-gray-400" /><input aria-label="Buscar cámaras" value={busqueda} onChange={(e) => setBusqueda(e.target.value)} placeholder="Buscar nombre, ubicación o ID" className={`${inputClass} pl-9`} /></label>
              <select aria-label="Filtrar cámaras por estado" value={filtro} onChange={(e) => setFiltro(e.target.value)} className="rounded-lg border border-gray-200 px-3 py-2 text-sm"><option value="activas">Activas</option><option value="inactivas">Inactivas</option><option value="todas">Todas</option></select>
            </div>
          </div>
          {loading ? <p className="p-5 text-sm text-gray-500">Cargando cámaras...</p> : error ? <p className="p-5 text-sm text-gray-500">No se pudo cargar una lista confiable.</p> : visibles.length === 0 ? <p className="p-5 text-sm text-gray-500">No hay cámaras que coincidan con el filtro.</p> : (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm">
                <thead className="bg-gray-50 text-xs uppercase text-gray-500"><tr><th className="px-4 py-3">Cámara</th><th className="px-4 py-3">Ubicación</th><th className="px-4 py-3">Estado</th><th className="px-4 py-3">Acciones</th></tr></thead>
                <tbody>{visibles.map((c) => <tr key={c.id} className={`border-t border-gray-100 ${editando?.id === c.id ? 'bg-green-50' : 'hover:bg-gray-50'}`}>
                  <td className="px-4 py-3 font-medium text-gray-800">{c.nombre}<span className="mt-1 block break-all font-mono text-[10px] font-normal text-gray-500">{c.id}</span></td>
                  <td className="px-4 py-3 text-gray-600">{c.ubicacion || '—'}</td>
                  <td className="px-4 py-3"><span className={`whitespace-nowrap rounded-full px-2 py-1 text-xs ${c.active ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-600'}`}>{c.active ? 'Activa' : 'Inactiva'}</span></td>
                  <td className="px-4 py-3"><div className="flex flex-wrap gap-2">
                    <button type="button" disabled={bloqueado} onClick={() => handleEditar(c)} className="inline-flex items-center gap-1 rounded-md border border-gray-200 px-2 py-1.5 text-xs font-medium text-gray-700 hover:bg-gray-100 disabled:opacity-50"><Pencil size={14} /> Editar</button>
                    <button type="button" disabled={bloqueado} onClick={() => setPorEliminar(c)} className="inline-flex items-center gap-1 rounded-md border border-red-200 px-2 py-1.5 text-xs font-medium text-red-700 hover:bg-red-50 disabled:opacity-50"><Trash2 size={14} /> Eliminar</button>
                  </div></td>
                </tr>)}</tbody>
              </table>
            </div>
          )}
          {!loading && !error && <p className="border-t border-gray-100 px-5 py-3 text-xs text-gray-500">Mostrando {visibles.length} de {lista.length} cámaras registradas.</p>}
        </section>
      </div>
      {porEliminar && <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
        <section role="alertdialog" aria-modal="true" aria-labelledby="confirmar-eliminar" aria-describedby="detalle-eliminar" className="w-full max-w-md rounded-xl bg-white p-6 shadow-xl">
          <div className="flex items-center justify-between"><div className="rounded-lg bg-red-50 p-2 text-red-600"><Trash2 size={24} /></div><button type="button" disabled={busy} aria-label="Cerrar" onClick={() => setPorEliminar(null)} className="text-gray-500 disabled:opacity-50"><X size={20} /></button></div>
          <h2 id="confirmar-eliminar" className="mt-4 text-lg font-semibold text-gray-800">¿Eliminar definitivamente la cámara?</h2>
          <div id="detalle-eliminar" className="mt-2 space-y-2 text-sm text-gray-600"><p className="font-semibold text-gray-800">{porEliminar.nombre}</p><p className="break-all font-mono text-xs">{porEliminar.id}</p><p>Esta acción puede borrar de forma irreversible sus sensores, mediciones, predicciones, alertas y registros históricos asociados. Si necesitas conservarlos, cancela y desactiva la cámara desde Editar.</p></div>
          <div className="mt-5 flex flex-wrap justify-end gap-2"><button autoFocus type="button" disabled={busy} onClick={() => setPorEliminar(null)} className="rounded-lg border border-gray-200 px-4 py-2 text-sm disabled:opacity-50">Cancelar</button><button type="button" disabled={bloqueado} onClick={handleEliminar} className="rounded-lg bg-red-600 px-4 py-2 text-sm font-medium text-white hover:bg-red-700 disabled:opacity-50">{busy ? 'Eliminando...' : 'Eliminar definitivamente'}</button></div>
        </section>
      </div>}
    </div>
  );
};

export default Camaras;