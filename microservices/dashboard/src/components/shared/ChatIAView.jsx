import React, { useState, useRef, useEffect } from 'react';
import { Send, Bot, User, AlertCircle } from 'lucide-react';
import { preguntarIA } from '../../api/gemini';

const CAMARAS_DEMO = ['Cámara Principal 01', 'Cámara Principal 02', 'Cámara Secundaria 01'];

// Asistente conversacional (CU-09). Si Gemini no responde, el chat sigue
// funcionando con una respuesta de ejemplo y avisa que la IA no está
// disponible, sin bloquear el resto del dashboard (RNF tolerancia a fallos).
const ChatIAView = () => {
  const [camara, setCamara] = useState(CAMARAS_DEMO[0]);
  const [mensajes, setMensajes] = useState([
    { rol: 'ia', texto: 'Hola, soy el asistente de monitoreo. Selecciona una cámara y pregúntame sobre su estado, temperatura o alertas recientes.' },
  ]);
  const [pregunta, setPregunta] = useState('');
  const [enviando, setEnviando] = useState(false);
  const [iaCaida, setIaCaida] = useState(false);
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
      setMensajes((m) => [...m, { rol: 'ia', texto: respuesta?.respuesta || respuesta?.texto || 'Sin respuesta.' }]);
    } catch (err) {
      setIaCaida(true);
      setMensajes((m) => [...m, {
        rol: 'ia',
        texto: `Basándome en los últimos datos registrados de ${camara}, no se detectan anomalías recientes. (Respuesta de ejemplo: el servicio Gemini no respondió).`,
      }]);
    } finally {
      setEnviando(false);
    }
  };

  return (
    <div className="flex flex-col h-full">
      <div className="flex items-center justify-between mb-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-800">Asistente IA</h1>
          <p className="text-sm text-gray-500">Preguntas en lenguaje natural sobre tus cámaras</p>
        </div>
        <select
          value={camara}
          onChange={(e) => setCamara(e.target.value)}
          className="border border-gray-200 rounded-lg px-3 py-2 text-sm bg-white"
        >
          {CAMARAS_DEMO.map((c) => (
            <option key={c} value={c}>{c}</option>
          ))}
        </select>
      </div>

      {iaCaida && (
        <div className="flex items-center gap-2 text-sm text-yellow-700 bg-yellow-50 px-4 py-2 rounded-lg mb-4">
          <AlertCircle size={16} />
          IA no disponible en este momento. El resto del dashboard sigue funcionando con normalidad.
        </div>
      )}

      <div className="bg-white rounded-lg shadow-md flex-1 flex flex-col overflow-hidden" style={{ minHeight: '420px' }}>
        <div className="flex-1 overflow-y-auto p-6 space-y-4">
          {mensajes.map((m, i) => (
            <div key={i} className={`flex gap-3 ${m.rol === 'usuario' ? 'justify-end' : ''}`}>
              {m.rol === 'ia' && (
                <div className="w-8 h-8 rounded-full bg-green-100 text-green-600 flex items-center justify-center shrink-0">
                  <Bot size={16} />
                </div>
              )}
              <div className={`max-w-md px-4 py-2 rounded-2xl text-sm ${
                m.rol === 'usuario' ? 'bg-green-600 text-white rounded-br-sm' : 'bg-gray-100 text-gray-700 rounded-bl-sm'
              }`}>
                {m.texto}
              </div>
              {m.rol === 'usuario' && (
                <div className="w-8 h-8 rounded-full bg-gray-200 text-gray-600 flex items-center justify-center shrink-0">
                  <User size={16} />
                </div>
              )}
            </div>
          ))}
          {enviando && <p className="text-xs text-gray-400 pl-11">Escribiendo...</p>}
          <div ref={bottomRef} />
        </div>

        <form onSubmit={handleEnviar} className="border-t border-gray-100 p-4 flex gap-3">
          <input
            type="text"
            value={pregunta}
            onChange={(e) => setPregunta(e.target.value)}
            placeholder={`Pregunta algo sobre ${camara}...`}
            className="flex-1 border border-gray-200 rounded-lg px-4 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-green-500"
          />
          <button
            type="submit"
            disabled={enviando}
            className="bg-green-600 hover:bg-green-700 text-white rounded-lg px-4 py-2 flex items-center gap-2 text-sm disabled:opacity-50"
          >
            <Send size={16} /> Enviar
          </button>
        </form>
      </div>
    </div>
  );
};

export default ChatIAView;
