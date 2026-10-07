import React, { useState, useRef, useEffect } from 'react';
import {
  Send, Bot, User, AlertCircle, X, Paperclip, Mic,
  ClipboardList, History, Maximize2, Sparkles, Bell, HelpCircle, Download,
} from 'lucide-react';
import { preguntarIA } from '../../api/gemini';

const CAMARAS_DEMO = [
  'Todas las Cámaras',
  'Cámara Principal 01',
  'Cámara Principal 02',
  'Cámara Secundaria 01',
];

const SUGERENCIAS_RAPIDAS = [
  '¿Hubo algún evento fuera de rango en las últimas 24 horas?',
  '¿Cuál es el promedio de temperatura del turno de la mañana?',
  '¿Hay correlación entre el consumo eléctrico y la temperatura?',
];

// ============================================================
// COMPONENTE
// ============================================================
const ChatIAView = () => {
  const [camara, setCamara] = useState(CAMARAS_DEMO[0]);
  const [mensajes, setMensajes] = useState([
    {
      rol: 'ia',
      texto: 'Hola, soy CryoBot, tu asistente de monitoreo. Selecciona una cámara y pregúntame sobre su estado, temperatura o alertas recientes.',
    },
  ]);
  const [pregunta, setPregunta] = useState('');
  const [enviando, setEnviando] = useState(false);
  const [iaCaida, setIaCaida] = useState(false);
  const [bannerCerrado, setBannerCerrado] = useState(false);
  const bottomRef = useRef(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [mensajes]);

  const handleEnviar = async (e) => {
    e.preventDefault();
    if (!pregunta.trim()) return;

    const preguntaActual = pregunta;
    setMensajes((m) => [...m, { rol: 'usuario', texto: preguntaActual }]);
    setPregunta('');
    setEnviando(true);

    try {
      const respuesta = await preguntarIA(preguntaActual, camara);
      setIaCaida(false);
      setMensajes((m) => [
        ...m,
        { rol: 'ia', texto: respuesta?.respuesta || respuesta?.texto || 'Sin respuesta.' },
      ]);
    } catch (err) {
      setIaCaida(true);
      setMensajes((m) => [
        ...m,
        {
          rol: 'ia',
          texto: `Basándome en los últimos datos registrados de ${camara}, no se detectan anomalías recientes. (Respuesta de ejemplo: el servicio Gemini no respondió).`,
        },
      ]);
    } finally {
      setEnviando(false);
    }
  };

  return (
    <div className="flex flex-col h-full">
      {/* ==================================================== */}
      {/* HEADER SUPERIOR */}
      {/* ==================================================== */}
      <div className="flex items-center justify-end gap-3 mb-4">
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
      {/* BANNER: IA NO DISPONIBLE */}
      {/* ==================================================== */}
      {iaCaida && !bannerCerrado && (
        <div className="flex items-center justify-between bg-yellow-50 border border-yellow-200 text-yellow-800 px-4 py-2.5 rounded-lg mb-4">
          <div className="flex items-center gap-2 text-sm">
            <AlertCircle size={16} />
            IA no disponible, mostrando datos sin procesar
          </div>
          <button
            onClick={() => setBannerCerrado(true)}
            className="p-1 rounded hover:bg-yellow-100"
          >
            <X size={16} />
          </button>
        </div>
      )}

      {/* ==================================================== */}
      {/* TARJETA DEL CHAT */}
      {/* ==================================================== */}
      <div className="bg-white rounded-lg shadow-md flex-1 flex flex-col overflow-hidden">
        {/* Header del chat */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-100">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-lg bg-green-100 flex items-center justify-center">
              <Bot size={20} className="text-green-600" />
            </div>
            <div>
              <h2 className="font-semibold text-gray-800">CryoBot Asistente</h2>
              <p className="text-xs text-gray-500">Análisis predictivo y consultas técnicas</p>
            </div>
          </div>
          <div className="flex items-center gap-3">
            <span className="inline-flex items-center gap-1 text-xs text-green-700 bg-green-50 px-3 py-1 rounded-full">
              <Sparkles size={12} />
              Contexto histórico incluido (mediciones, alertas)
            </span>
            <div className="flex items-center gap-2">
              <span className="text-xs text-gray-500">Contexto:</span>
              <select
                value={camara}
                onChange={(e) => setCamara(e.target.value)}
                className="border border-gray-200 rounded-lg px-3 py-1.5 text-sm bg-white focus:outline-none focus:ring-2 focus:ring-green-500"
              >
                {CAMARAS_DEMO.map((c) => (
                  <option key={c} value={c}>{c}</option>
                ))}
              </select>
            </div>
          </div>
        </div>

        {/* Mensajes */}
        <div className="flex-1 overflow-y-auto p-6 space-y-6">
          {mensajes.map((m, i) => (
            <div key={i}>
              {m.rol === 'ia' ? (
                <div className="flex gap-3">
                  <div className="w-8 h-8 rounded-full bg-green-100 text-green-600 flex items-center justify-center shrink-0">
                    <Bot size={16} />
                  </div>
                  <div className="flex-1">
                    <p className="text-xs font-medium text-gray-700 mb-1">CryoBot</p>
                    <div className="bg-gray-50 border border-gray-100 text-gray-700 rounded-2xl rounded-tl-sm px-4 py-3 text-sm">
                      {m.texto}
                    </div>
                    {/* Si el mensaje es de IA, mostramos las tarjetas de acción */}
                    {i > 0 && (
                      <div className="flex flex-wrap gap-2 mt-3">
                        <button className="inline-flex items-center gap-2 text-xs text-gray-600 bg-white border border-gray-200 px-3 py-2 rounded-lg hover:bg-gray-50">
                          <ClipboardList size={14} />
                          Generar Orden de Trabajo
                        </button>
                        <button className="inline-flex items-center gap-2 text-xs text-gray-600 bg-white border border-gray-200 px-3 py-2 rounded-lg hover:bg-gray-50">
                          <History size={14} />
                          Ver ciclo anterior
                        </button>
                      </div>
                    )}
                  </div>
                </div>
              ) : (
                <div className="flex gap-3 justify-end">
                  <div className="flex flex-col items-end">
                    <p className="text-xs font-medium text-gray-700 mb-1">Tú</p>
                    <div className="bg-blue-100 text-blue-900 rounded-2xl rounded-tr-sm px-4 py-3 text-sm max-w-lg">
                      {m.texto}
                    </div>
                  </div>
                  <div className="w-8 h-8 rounded-full bg-gray-200 text-gray-600 flex items-center justify-center shrink-0">
                    <User size={16} />
                  </div>
                </div>
              )}
            </div>
          ))}

          {/* Sugerencias rápidas (solo al inicio) */}
          {mensajes.length === 1 && (
            <div className="flex flex-wrap gap-2 pl-11">
              {SUGERENCIAS_RAPIDAS.map((s, i) => (
                <button
                  key={i}
                  onClick={() => setPregunta(s)}
                  className="text-xs text-gray-600 bg-gray-50 border border-gray-200 px-3 py-2 rounded-full hover:bg-gray-100"
                >
                  {s}
                </button>
              ))}
            </div>
          )}

          {enviando && (
            <div className="flex gap-3">
              <div className="w-8 h-8 rounded-full bg-green-100 text-green-600 flex items-center justify-center shrink-0">
                <Bot size={16} />
              </div>
              <p className="text-xs text-gray-400 self-center">Escribiendo...</p>
            </div>
          )}

          <div ref={bottomRef} />
        </div>

        {/* Input */}
        <div className="border-t border-gray-100 p-4">
          <form onSubmit={handleEnviar} className="flex items-center gap-3 bg-gray-50 border border-gray-200 rounded-xl px-4 py-2">
            <button type="button" className="p-1.5 rounded-lg hover:bg-gray-200">
              <Paperclip size={18} className="text-gray-500" />
            </button>
            <input
              type="text"
              value={pregunta}
              onChange={(e) => setPregunta(e.target.value)}
              placeholder="Escribe tu consulta o pide un análisis de datos..."
              className="flex-1 bg-transparent text-sm focus:outline-none"
            />
            <button type="button" className="p-1.5 rounded-lg hover:bg-gray-200">
              <Mic size={18} className="text-gray-500" />
            </button>
            <button
              type="submit"
              disabled={enviando}
              className="bg-green-600 hover:bg-green-700 text-white rounded-lg p-2 disabled:opacity-50"
            >
              <Send size={18} />
            </button>
          </form>
        </div>
      </div>

      {/* ==================================================== */}
      {/* FOOTER */}
      {/* ==================================================== */}
      <div className="flex items-center justify-between mt-3 text-xs text-gray-400">
        <span>El asistente puede cometer errores. Verifica los datos críticos.</span>
        <a href="#" className="text-green-600 hover:text-green-700 font-medium">
          Ver Documentación de la API
        </a>
      </div>
    </div>
  );
};

export default ChatIAView;