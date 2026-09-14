import React from 'react';
import { HelpCircle, Mail, Phone, LifeBuoy } from 'lucide-react';

const FAQS = [
  { q: '¿Qué significa una alerta HACCP activa?', a: 'Indica que una cámara superó los umbrales de temperatura configurados y requiere atención inmediata para evitar una rotura de la cadena de frío.' },
  { q: '¿Por qué no veo la sección de Optimización y Ahorro?', a: 'Esa sección está disponible solo para el rol Gerente. Si necesitas acceso, contacta al administrador del sistema.' },
  { q: '¿Qué hago si el Asistente IA no responde?', a: 'El resto del dashboard sigue funcionando con normalidad; el servicio de IA es un complemento. Intenta nuevamente en unos minutos.' },
  { q: '¿Cómo reconozco o resuelvo una alerta?', a: 'Desde Alertas HACCP, el rol Técnico puede reconocer una alerta y luego marcarla como resuelta una vez solucionado el problema.' },
];

// Ayuda y Soporte (Gerente y Técnico) — información de contacto y FAQ.
const Soporte = () => {
  return (
    <div>
      <h1 className="text-2xl font-bold text-gray-800 mb-1">Ayuda y Soporte</h1>
      <p className="text-sm text-gray-500 mb-6">Contacta al administrador del sistema o revisa las preguntas frecuentes</p>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
        <div className="bg-white p-6 rounded-lg shadow-md flex items-start gap-4">
          <div className="p-3 rounded-lg bg-green-50 text-green-600"><Mail size={20} /></div>
          <div>
            <p className="text-sm text-gray-500">Correo de soporte</p>
            <p className="font-medium text-gray-800">soporte@cryometric.cl</p>
          </div>
        </div>
        <div className="bg-white p-6 rounded-lg shadow-md flex items-start gap-4">
          <div className="p-3 rounded-lg bg-green-50 text-green-600"><Phone size={20} /></div>
          <div>
            <p className="text-sm text-gray-500">Línea de emergencia HACCP</p>
            <p className="font-medium text-gray-800">+56 9 0000 0000</p>
          </div>
        </div>
      </div>

      <div className="bg-white rounded-lg shadow-md">
        <div className="px-6 py-4 border-b border-gray-100 flex items-center gap-2">
          <LifeBuoy size={18} className="text-gray-500" />
          <h2 className="text-lg font-semibold text-gray-700">Preguntas frecuentes</h2>
        </div>
        <div className="divide-y divide-gray-100">
          {FAQS.map((f, i) => (
            <details key={i} className="px-6 py-4 group">
              <summary className="flex items-center gap-2 cursor-pointer text-sm font-medium text-gray-700">
                <HelpCircle size={16} className="text-green-600" /> {f.q}
              </summary>
              <p className="text-sm text-gray-500 mt-2 pl-6">{f.a}</p>
            </details>
          ))}
        </div>
      </div>
    </div>
  );
};

export default Soporte;
