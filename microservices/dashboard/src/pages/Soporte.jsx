import React from 'react';
import {
  HelpCircle, Mail, Phone, LifeBuoy, MessageSquare,
  Bell, Search, Download, User, ChevronDown,
} from 'lucide-react';

// ============================================================
// PREGUNTAS FRECUENTES
// ============================================================
const FAQS = [
  {
    q: '¿Qué significa una alerta HACCP activa?',
    a: 'Indica que una cámara superó los umbrales de temperatura configurados y requiere atención inmediata para evitar una rotura de la cadena de frío.',
  },
  {
    q: '¿Por qué no veo la sección de Optimización y Ahorro?',
    a: 'Esa sección está disponible solo para el rol Gerente. Si necesitas acceso, contacta al administrador del sistema.',
  },
  {
    q: '¿Qué hago si el Asistente IA no responde?',
    a: 'El resto del dashboard sigue funcionando con normalidad; el servicio de IA es un complemento. Intenta nuevamente en unos minutos.',
  },
  {
    q: '¿Cómo reconozco o resuelvo una alerta?',
    a: 'Desde Alertas HACCP, el rol Técnico puede reconocer una alerta y luego marcarla como resuelta una vez solucionado el problema.',
  },
  {
    q: '¿Con qué frecuencia se actualizan los datos?',
    a: 'Los datos de temperatura y consumo se actualizan cada 10 segundos. Las predicciones se recalculan cada minuto y las recomendaciones de ahorro cada 6 horas.',
  },
  {
    q: '¿Cómo exporto un reporte histórico?',
    a: 'Desde la sección Historial y Reportes, selecciona el rango de fechas y haz clic en "Exportar" para descargar en formato CSV o PDF.',
  },
];

// ============================================================
// COMPONENTE
// ============================================================
const Soporte = () => {
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
          <User size={18} className="text-gray-600" />
        </div>
      </div>

      {/* ==================================================== */}
      {/* TÍTULO */}
      {/* ==================================================== */}
      <div className="mb-6">
        <div className="flex items-center gap-3 mb-1">
          <div className="p-2 bg-green-50 rounded-lg">
            <LifeBuoy size={22} className="text-green-600" />
          </div>
          <div>
            <h1 className="text-2xl font-bold text-gray-800">Ayuda y Soporte</h1>
            <p className="text-sm text-gray-500">
              Contacta al administrador o revisa las preguntas frecuentes
            </p>
          </div>
        </div>
      </div>

      {/* ==================================================== */}
      {/* TARJETAS DE CONTACTO */}
      {/* ==================================================== */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
        {/* Correo */}
        <div className="bg-white p-6 rounded-lg shadow-md border-l-4 border-green-500">
          <div className="flex items-start gap-4">
            <div className="p-3 rounded-lg bg-green-50">
              <Mail size={22} className="text-green-600" />
            </div>
            <div className="flex-1">
              <p className="text-xs text-gray-500 uppercase font-medium tracking-wide">
                Correo de Soporte
              </p>
              <p className="font-semibold text-gray-800 mt-1">soporte@cryometric.cl</p>
              <p className="text-xs text-gray-400 mt-1">Respuesta en 24h hábiles</p>
            </div>
          </div>
        </div>

        {/* Teléfono */}
        <div className="bg-white p-6 rounded-lg shadow-md border-l-4 border-red-500">
          <div className="flex items-start gap-4">
            <div className="p-3 rounded-lg bg-red-50">
              <Phone size={22} className="text-red-600" />
            </div>
            <div className="flex-1">
              <p className="text-xs text-gray-500 uppercase font-medium tracking-wide">
                Emergencia HACCP
              </p>
              <p className="font-semibold text-gray-800 mt-1">+56 9 0000 0000</p>
              <p className="text-xs text-gray-400 mt-1">Disponible 24/7</p>
            </div>
          </div>
        </div>

        {/* Chat */}
        <div className="bg-white p-6 rounded-lg shadow-md border-l-4 border-blue-500">
          <div className="flex items-start gap-4">
            <div className="p-3 rounded-lg bg-blue-50">
              <MessageSquare size={22} className="text-blue-600" />
            </div>
            <div className="flex-1">
              <p className="text-xs text-gray-500 uppercase font-medium tracking-wide">
                Asistente IA
              </p>
              <p className="font-semibold text-gray-800 mt-1">CryoBot</p>
              <p className="text-xs text-gray-400 mt-1">
                Consultas técnicas en tiempo real
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* ==================================================== */}
      {/* PREGUNTAS FRECUENTES */}
      {/* ==================================================== */}
      <div className="bg-white rounded-lg shadow-md overflow-hidden">
        <div className="px-6 py-5 border-b border-gray-100 flex items-center gap-2">
          <HelpCircle size={18} className="text-green-600" />
          <h2 className="text-lg font-semibold text-gray-800">Preguntas Frecuentes</h2>
          <span className="ml-auto text-xs text-gray-500 bg-gray-100 px-2 py-1 rounded">
            {FAQS.length} preguntas
          </span>
        </div>

        <div className="divide-y divide-gray-100">
          {FAQS.map((f, i) => (
            <details key={i} className="group px-6 py-4 hover:bg-gray-50 transition-colors">
              <summary className="flex items-center justify-between cursor-pointer list-none">
                <div className="flex items-center gap-3">
                  <div className="w-6 h-6 rounded-full bg-green-50 text-green-600 flex items-center justify-center text-xs font-semibold">
                    {i + 1}
                  </div>
                  <span className="text-sm font-medium text-gray-800">{f.q}</span>
                </div>
                <ChevronDown
                  size={16}
                  className="text-gray-400 group-open:rotate-180 transition-transform"
                />
              </summary>
              <p className="text-sm text-gray-600 mt-3 pl-9 leading-relaxed">{f.a}</p>
            </details>
          ))}
        </div>
      </div>

      {/* ==================================================== */}
      {/* FOOTER */}
      {/* ==================================================== */}
      <div className="mt-6 bg-blue-50 border border-blue-200 rounded-lg px-6 py-4 flex items-center justify-between">
        <div>
          <p className="text-sm font-medium text-blue-900">
            ¿No encuentras lo que buscas?
          </p>
          <p className="text-xs text-blue-700 mt-1">
            Contacta directamente al administrador del sistema.
          </p>
        </div>
        <button className="flex items-center gap-2 bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg text-sm font-medium">
          <Mail size={16} />
          Contactar
        </button>
      </div>
    </div>
  );
};

export default Soporte;