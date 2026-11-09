import React, { useState } from 'react';
import {
  TrendingUp, Download, Lightbulb, Search, Bell, HelpCircle,
  User, FileText, Zap, ThermometerSnowflake, Snowflake,
} from 'lucide-react';
import { useFetch } from '../../hooks/useApi';
import { getRecomendacionesAhorro, exportarReporte } from '../../api/optimizacion';
import { formatCLP } from '../../utils/formatters';
import ConsumptionForecastChart from '../../components/charts/ConsumptionForecastChart';

// ============================================================
// DATOS MOCK
// ============================================================
const MOCK_RECOMENDACIONES = [
  {
    id: 1,
    titulo: 'Ajuste de Setpoint Cámara 3',
    descripcion: 'Elevar el setpoint en horario valle (02:00 - 06:00) mantendrá la cadena de frío (-18°C) reduciendo ciclos del compresor.',
    prioridad: 'alta',
    porcentaje_ahorro: 15,
    monto_clp: 45000,
    icono: 'snowflake',
  },
  {
    id: 2,
    titulo: 'Optimización Defrost Cámara 1',
    descripcion: 'Retrasar el ciclo de deshielo programado 45 minutos para evitar solapamiento con pico tarifario.',
    prioridad: 'media',
    porcentaje_ahorro: 8,
    monto_clp: 28000,
    icono: 'thermometer',
  },
  {
    id: 3,
    titulo: 'Secuenciación de Compresores',
    descripcion: 'Implementar arranque escalonado en Planta Central para reducir penalizaciones por demanda máxima de kW.',
    prioridad: 'media',
    porcentaje_ahorro: 12,
    monto_clp: 77000,
    icono: 'zap',
  },
];

const prioridadConfig = {
  alta: { label: 'Alta Prioridad', color: 'yellow' },
  media: { label: 'Media Prioridad', color: 'blue' },
  baja: { label: 'Baja Prioridad', color: 'gray' },
};

const iconoConfig = {
  snowflake: Snowflake,
  thermometer: ThermometerSnowflake,
  zap: Zap,
};


// ============================================================
// FORMATEO DE RECOMENDACIONES REALES
// ============================================================

const accionConfig = {
  reducir_carga: 'Reducir carga',
  apagar: 'Apagar equipo',
  encender: 'Encender equipo',
  mantener: 'Mantener operación',
};

const equipoConfig = {
  eq_climatizacion_zona_b: 'Climatización Zona B',
  camaras_2_y_3: 'Cámaras 2 y 3',
};

const formatTextoTecnico = (valor) => {
  if (!valor) return 'No especificado';

  return String(valor)
    .replace(/^eq_/, '')
    .replaceAll('_', ' ')
    .replace(/\b\w/g, (letra) => letra.toUpperCase());
};

const formatAccion = (accion) => {
  if (accionConfig[accion]) return accionConfig[accion];
  return String(accion).includes('_') ? formatTextoTecnico(accion) : String(accion);
};

const formatEquipo = (equipo) => {
  return equipoConfig[equipo] || formatTextoTecnico(equipo);
};

const parseDescripcionRecomendacion = (descripcion) => {
  if (!descripcion) return null;

  if (typeof descripcion === 'object' && !Array.isArray(descripcion)) {
    return descripcion;
  }

  if (typeof descripcion !== 'string') {
    return null;
  }

  try {
    const parsed = JSON.parse(descripcion);

    if (
      parsed &&
      typeof parsed === 'object' &&
      !Array.isArray(parsed)
    ) {
      return parsed;
    }
  } catch {
    // Si no es JSON, se muestra como descripción normal.
  }

  return null;
};

const formatFecha = (fecha) => {
  if (!fecha) return 'No especificada';

  const partes = String(fecha).split('-');

  if (partes.length !== 3) {
    return fecha;
  }

  const [anio, mes, dia] = partes;
  return `${dia}/${mes}/${anio}`;
};

const formatVentana = (ventana) => {
  if (!Array.isArray(ventana) || ventana.length < 2) {
    return 'No especificada';
  }

  return `${ventana[0]} - ${ventana[1]}`;
};

const formatPrecioEnergia = (precio) => {
  if (precio === null || precio === undefined) {
    return 'No especificado';
  }

  const numero = Number(precio);

  if (!Number.isFinite(numero)) {
    return 'No especificado';
  }

  return `${numero.toLocaleString('es-CL', {
    maximumFractionDigits: 2,
  })} CLP/kWh`;
};



// ============================================================
// COMPONENTE PRINCIPAL
// ============================================================
const Ahorro = () => {
  const { data: recomendaciones, loading, isFallback } = useFetch(
    getRecomendacionesAhorro,
    [],
    MOCK_RECOMENDACIONES
  );
  const [exportando, setExportando] = useState(false);

  const lista = Array.isArray(recomendaciones) ? recomendaciones : [];
  const totalAhorro = lista.reduce((acc, r) => acc + (r.monto_clp || 0), 0);

  const handleExportar = async (formato) => {
    setExportando(true);
    try {
      const blob = await exportarReporte(formato);
      const url = window.URL.createObjectURL(new Blob([blob]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `optimizacion.${formato}`);
      document.body.appendChild(link);
      link.click();
      link.remove();
    } catch (err) {
      alert('No se pudo exportar el reporte: el servicio aún no está disponible.');
    } finally {
      setExportando(false);
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
      {/* TÍTULO + BOTONES */}
      {/* ==================================================== */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-800">Optimización y Ahorro</h1>
          <p className="text-sm text-gray-500">Análisis predictivo de consumo energético (Vista Gerencial)</p>
        </div>
        <div className="flex gap-3">
          <button className="flex items-center gap-2 bg-green-500 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-green-600">
            <FileText size={16} />
            Generar Reporte
          </button>
          <button
            disabled={exportando}
            onClick={() => handleExportar('pdf')}
            className="flex items-center gap-2 bg-green-500 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-green-600"
          >
            <Download size={16} />
            Exportar Reporte
          </button>
        </div>
      </div>

      {isFallback && (
        <div className="text-xs text-yellow-600 bg-yellow-50 px-3 py-2 rounded-lg mb-4 inline-block">
          Mostrando datos de ejemplo (sin conexión con la API)
        </div>
      )}

      {/* ==================================================== */}
      {/* LAYOUT PRINCIPAL: TARJETA DE AHORRO + GRÁFICO */}
      {/* ==================================================== */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-8">
        {/* Tarjeta de Ahorro Total */}
        <div className="bg-white p-6 rounded-lg shadow-md flex flex-col justify-between">
          <div>
            <div className="flex items-center gap-2 mb-3">
              <TrendingUp size={18} className="text-green-600" />
              <p className="text-xs text-gray-500 font-medium uppercase tracking-wide">
                Ahorro Total Potencial
              </p>
            </div>
            <p className="text-4xl font-bold text-green-600">
              {formatCLP(totalAhorro)}
            </p>
            <p className="text-xs text-gray-500 mt-2">
              Suma de las recomendaciones de ahorro pendientes.
            </p>
          </div>
          <div className="mt-6 inline-flex items-center gap-1 text-xs text-green-700 bg-green-50 px-3 py-1 rounded-lg self-start">
            <TrendingUp size={12} />
            Ahorro potencial estimado
          </div>
        </div>

        {/* Gráfico de Proyección */}
        <div className="lg:col-span-2 bg-white p-6 rounded-lg shadow-md">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h2 className="text-lg font-semibold text-gray-800">
                Proyección de Consumo Energético
              </h2>
              <p className="text-xs text-gray-500">Histórico vs Pronóstico Prophet</p>
            </div>
            <div className="flex items-center gap-4 text-xs">
              <div className="flex items-center gap-2">
                <span className="w-4 h-0.5 bg-green-600"></span>
                <span className="text-gray-600">Histórico</span>
              </div>
              <div className="flex items-center gap-2">
                <span className="w-4 h-0.5 bg-yellow-500 border-dashed"></span>
                <span className="text-gray-600">Pronóstico IA</span>
              </div>
            </div>
          </div>
          <ConsumptionForecastChart />
        </div>
      </div>

      {/* ==================================================== */}
      {/* RECOMENDACIONES */}
      {/* ==================================================== */}
      <div className="mb-4">
        <h2 className="text-lg font-semibold text-gray-800">Recomendaciones de IA</h2>
      </div>

      {loading ? (
        <p className="text-sm text-gray-500">Cargando recomendaciones...</p>
      ) : lista.length === 0 ? (
        <p className="text-sm text-gray-500">Aún no hay recomendaciones de ahorro disponibles.</p>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
         {lista.map((r) => {
            const prioridad =
              prioridadConfig[r.prioridad] || prioridadConfig.media;

            const Icono = iconoConfig[r.icono] || Lightbulb;

            const detalles = parseDescripcionRecomendacion(r.descripcion);

            const equipo = detalles?.equipment;
            const fechaObjetivo = detalles?.target_date;
            const ventana = detalles?.window;
            const horas = detalles?.hours;
            const precioEnergia = detalles?.price_clp_kwh;

            return (
              <div
                key={r.id}
                className="bg-white p-6 rounded-xl shadow-md border border-gray-100 flex flex-col hover:shadow-lg transition-shadow"
              >
                {/* Header */}
                <div className="flex items-start justify-between mb-5">
                  <div className="p-3 rounded-xl bg-green-50 text-green-600">
                    <Icono size={22} />
                  </div>

                  <span
                    className={`text-xs px-3 py-1 rounded-full font-medium ${
                      prioridad.color === 'yellow'
                        ? 'bg-yellow-100 text-yellow-700'
                        : prioridad.color === 'blue'
                        ? 'bg-blue-100 text-blue-700'
                        : 'bg-gray-100 text-gray-600'
                    }`}
                  >
                    {prioridad.label}
                  </span>
                </div>

                {/* Acción */}
                <h3 className="text-lg font-semibold text-gray-800 mb-1">
                  {formatAccion(r.titulo)}
                </h3>

                <p className="text-xs text-gray-400 mb-5">
                  Recomendación de optimización energética
                </p>

                {/* Descripción estructurada */}
                {detalles ? (
                  <div className="space-y-3 mb-5 flex-1">
                    {detalles.rationale && (
                      <p className="text-sm text-gray-600 leading-relaxed">
                        {detalles.rationale}
                      </p>
                    )}
                    <div className="flex items-start justify-between gap-4">
                      <span className="text-sm text-gray-500">
                        Equipo
                      </span>

                      <span className="text-sm font-medium text-gray-800 text-right">
                        {formatEquipo(equipo)}
                      </span>
                    </div>

                    <div className="flex items-start justify-between gap-4">
                      <span className="text-sm text-gray-500">
                        Fecha objetivo
                      </span>

                      <span className="text-sm font-medium text-gray-800 text-right">
                        {formatFecha(fechaObjetivo)}
                      </span>
                    </div>

                    <div className="flex items-start justify-between gap-4">
                      <span className="text-sm text-gray-500">
                        Ventana horaria
                      </span>

                      <span className="text-sm font-medium text-gray-800 text-right">
                        {formatVentana(ventana)}
                      </span>
                    </div>

                    <div className="flex items-start justify-between gap-4">
                      <span className="text-sm text-gray-500">
                        Duración
                      </span>

                      <span className="text-sm font-medium text-gray-800 text-right">
                        {horas !== null && horas !== undefined
                          ? `${horas} ${Number(horas) === 1 ? 'hora' : 'horas'}`
                          : 'No especificada'}
                      </span>
                    </div>

                    <div className="flex items-start justify-between gap-4">
                      <span className="text-sm text-gray-500">
                        Precio energía
                      </span>

                      <span className="text-sm font-medium text-gray-800 text-right">
                        {formatPrecioEnergia(precioEnergia)}
                      </span>
                    </div>
                  </div>
                ) : (
                  <p className="text-sm text-gray-500 mb-5 flex-1 leading-relaxed">
                    {r.descripcion || 'Sin descripción disponible.'}
                  </p>
                )}

                {/* Ahorro */}
                <div className="grid grid-cols-2 gap-4 pt-4 border-t border-gray-100">
                  <div>
                    <p className="text-xs text-gray-400 uppercase tracking-wide">
                      Ahorro Est.
                    </p>

                    <p className="text-xl font-bold text-green-600 mt-1">
                      {r.porcentaje_ahorro ?? 0}%
                    </p>
                  </div>

                  <div>
                    <p className="text-xs text-gray-400 uppercase tracking-wide">
                      Impacto
                    </p>

                    <p className="text-xl font-bold text-gray-800 mt-1">
                      {formatCLP(r.monto_clp || 0)}
                    </p>
                  </div>
                </div>
              </div>
            );
          })}


        </div>
      )}
    </div>
  );
};

export default Ahorro;
