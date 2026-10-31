import React, {
  useEffect,
  useRef,
  useState,
} from 'react';

import {
  AlertCircle,
  Bell,
  Bot,
  ClipboardList,
  Download,
  HelpCircle,
  History,
  Mic,
  Paperclip,
  Send,
  Sparkles,
  User,
  X,
} from 'lucide-react';

import { preguntarIA } from '../../api/gemini';
import { getCamaras } from '../../api/camaras';


const SUGERENCIAS_RAPIDAS = [
  '¿Hubo algún evento fuera de rango en las últimas 24 horas?',
  '¿Cuál fue la temperatura promedio durante las últimas 24 horas?',
  '¿Hubo alertas críticas durante las últimas 24 horas?',
];


// ============================================================
// COMPONENTE
// ============================================================

const ChatIAView = () => {
  const [camaras, setCamaras] = useState([]);
  const [camaraId, setCamaraId] = useState('');

  const [mensajes, setMensajes] = useState([
    {
      rol: 'ia',
      texto:
        'Hola, soy CryoBot, tu asistente de monitoreo. ' +
        'Selecciona una cámara y pregúntame sobre su estado, ' +
        'temperatura o alertas recientes.',
    },
  ]);

  const [pregunta, setPregunta] = useState('');
  const [enviando, setEnviando] = useState(false);

  const [iaCaida, setIaCaida] = useState(false);
  const [bannerCerrado, setBannerCerrado] = useState(false);

  const [errorCamaras, setErrorCamaras] = useState(false);

  const bottomRef = useRef(null);


  // ============================================================
  // CARGAR CÁMARAS REALES DESDE EL BACKEND
  // ============================================================

  useEffect(() => {
    const cargarCamaras = async () => {
      try {
        const data = await getCamaras();

        setCamaras(data);
        setErrorCamaras(false);

        if (data.length > 0) {
          setCamaraId(data[0].id);
        }
      } catch (error) {
        console.error(
          'No se pudieron cargar las cámaras:',
          error
        );

        setErrorCamaras(true);
      }
    };

    cargarCamaras();
  }, []);


  // ============================================================
  // SCROLL AUTOMÁTICO DEL CHAT
  // ============================================================

  useEffect(() => {
    bottomRef.current?.scrollIntoView({
      behavior: 'smooth',
    });
  }, [mensajes]);


  // ============================================================
  // ENVIAR PREGUNTA A GEMINI
  // ============================================================

  const handleEnviar = async (e) => {
    e.preventDefault();

    const preguntaLimpia = pregunta.trim();

    if (!preguntaLimpia) {
      return;
    }

    if (!camaraId) {
      setMensajes((mensajesActuales) => [
        ...mensajesActuales,
        {
          rol: 'ia',
          texto:
            'Debes seleccionar una cámara antes de realizar la consulta.',
        },
      ]);

      return;
    }

    const preguntaActual = preguntaLimpia;

    setMensajes((mensajesActuales) => [
      ...mensajesActuales,
      {
        rol: 'usuario',
        texto: preguntaActual,
      },
    ]);

    setPregunta('');
    setEnviando(true);
    setBannerCerrado(false);

    try {
      const respuesta = await preguntarIA(
        preguntaActual,
        camaraId
      );

      setIaCaida(false);

      setMensajes((mensajesActuales) => [
        ...mensajesActuales,
        {
          rol: 'ia',
          texto:
            respuesta?.respuesta ||
            respuesta?.texto ||
            'Gemini respondió sin contenido.',
        },
      ]);
    } catch (error) {
      console.error(
        'Error consultando Gemini:',
        error
      );

      setIaCaida(true);

      setMensajes((mensajesActuales) => [
        ...mensajesActuales,
        {
          rol: 'ia',
          texto:
            error?.message ||
            'IA no disponible en este momento. ' +
              'El monitoreo del Dashboard continúa operativo.',
        },
      ]);
    } finally {
      setEnviando(false);
    }
  };


  // ============================================================
  // RENDER
  // ============================================================

  return (
    <div className="flex flex-col h-full">

      {/* ====================================================== */}
      {/* HEADER SUPERIOR */}
      {/* ====================================================== */}

      <div className="flex items-center justify-end gap-3 mb-4">
        <button
          type="button"
          className="relative p-2 rounded-full hover:bg-gray-100"
        >
          <Bell
            size={20}
            className="text-gray-600"
          />

          <span className="absolute top-1 right-1 w-2 h-2 bg-red-500 rounded-full" />
        </button>

        <button
          type="button"
          className="p-2 rounded-full hover:bg-gray-100"
        >
          <HelpCircle
            size={20}
            className="text-gray-600"
          />
        </button>

        <button
          type="button"
          className="flex items-center gap-2 bg-green-500 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-green-600"
        >
          <Download size={16} />
          Descargar Reporte
        </button>

        <div className="w-9 h-9 rounded-full bg-gray-200 flex items-center justify-center">
          <User
            size={18}
            className="text-gray-600"
          />
        </div>
      </div>


      {/* ====================================================== */}
      {/* BANNER: ERROR CARGANDO CÁMARAS */}
      {/* ====================================================== */}

      {errorCamaras && (
        <div className="flex items-center gap-2 bg-red-50 border border-red-200 text-red-800 px-4 py-2.5 rounded-lg mb-4">
          <AlertCircle size={16} />

          <span className="text-sm">
            No fue posible cargar las cámaras disponibles.
          </span>
        </div>
      )}


      {/* ====================================================== */}
      {/* BANNER: IA NO DISPONIBLE */}
      {/* ====================================================== */}

      {iaCaida && !bannerCerrado && (
        <div className="flex items-center justify-between bg-yellow-50 border border-yellow-200 text-yellow-800 px-4 py-2.5 rounded-lg mb-4">

          <div className="flex items-center gap-2 text-sm">
            <AlertCircle size={16} />

            IA no disponible. El monitoreo del Dashboard
            continúa operativo.
          </div>

          <button
            type="button"
            onClick={() => setBannerCerrado(true)}
            className="p-1 rounded hover:bg-yellow-100"
          >
            <X size={16} />
          </button>

        </div>
      )}


      {/* ====================================================== */}
      {/* TARJETA DEL CHAT */}
      {/* ====================================================== */}

      <div className="bg-white rounded-lg shadow-md flex-1 flex flex-col overflow-hidden">

        {/* HEADER DEL CHAT */}

        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-100">

          <div className="flex items-center gap-3">

            <div className="w-10 h-10 rounded-lg bg-green-100 flex items-center justify-center">
              <Bot
                size={20}
                className="text-green-600"
              />
            </div>

            <div>
              <h2 className="font-semibold text-gray-800">
                CryoBot Asistente
              </h2>

              <p className="text-xs text-gray-500">
                Análisis de mediciones y alertas de CryoMetric
              </p>
            </div>

          </div>


          <div className="flex items-center gap-3">

            <span className="inline-flex items-center gap-1 text-xs text-green-700 bg-green-50 px-3 py-1 rounded-full">
              <Sparkles size={12} />

              Contexto histórico incluido
            </span>


            {/* SELECT DE CÁMARAS REALES */}

            <div className="flex items-center gap-2">

              <span className="text-xs text-gray-500">
                Contexto:
              </span>

              <select
                value={camaraId}
                onChange={(e) =>
                  setCamaraId(e.target.value)
                }
                disabled={
                  enviando ||
                  camaras.length === 0
                }
                className="border border-gray-200 rounded-lg px-3 py-1.5 text-sm bg-white focus:outline-none focus:ring-2 focus:ring-green-500 disabled:opacity-50"
              >

                {camaras.length === 0 && (
                  <option value="">
                    Sin cámaras disponibles
                  </option>
                )}

                {camaras.map((camara) => (
                  <option
                    key={camara.id}
                    value={camara.id}
                  >
                    {camara.nombre}
                  </option>
                ))}

              </select>

            </div>

          </div>

        </div>


        {/* ==================================================== */}
        {/* MENSAJES */}
        {/* ==================================================== */}

        <div className="flex-1 overflow-y-auto p-6 space-y-6">

          {mensajes.map((mensaje, index) => (

            <div key={index}>

              {mensaje.rol === 'ia' ? (

                <div className="flex gap-3">

                  <div className="w-8 h-8 rounded-full bg-green-100 text-green-600 flex items-center justify-center shrink-0">
                    <Bot size={16} />
                  </div>


                  <div className="flex-1">

                    <p className="text-xs font-medium text-gray-700 mb-1">
                      CryoBot
                    </p>

                    <div className="bg-gray-50 border border-gray-100 text-gray-700 rounded-2xl rounded-tl-sm px-4 py-3 text-sm whitespace-pre-line">
                      {mensaje.texto}
                    </div>


                    {index > 0 && (
                      <div className="flex flex-wrap gap-2 mt-3">

                        <button
                          type="button"
                          className="inline-flex items-center gap-2 text-xs text-gray-600 bg-white border border-gray-200 px-3 py-2 rounded-lg hover:bg-gray-50"
                        >
                          <ClipboardList size={14} />
                          Generar Orden de Trabajo
                        </button>

                        <button
                          type="button"
                          className="inline-flex items-center gap-2 text-xs text-gray-600 bg-white border border-gray-200 px-3 py-2 rounded-lg hover:bg-gray-50"
                        >
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

                    <p className="text-xs font-medium text-gray-700 mb-1">
                      Tú
                    </p>

                    <div className="bg-blue-100 text-blue-900 rounded-2xl rounded-tr-sm px-4 py-3 text-sm max-w-lg">
                      {mensaje.texto}
                    </div>

                  </div>


                  <div className="w-8 h-8 rounded-full bg-gray-200 text-gray-600 flex items-center justify-center shrink-0">
                    <User size={16} />
                  </div>

                </div>

              )}

            </div>

          ))}


          {/* ================================================== */}
          {/* SUGERENCIAS RÁPIDAS */}
          {/* ================================================== */}

          {mensajes.length === 1 && (
            <div className="flex flex-wrap gap-2 pl-11">

              {SUGERENCIAS_RAPIDAS.map(
                (sugerencia, index) => (

                  <button
                    type="button"
                    key={index}
                    onClick={() =>
                      setPregunta(sugerencia)
                    }
                    className="text-xs text-gray-600 bg-gray-50 border border-gray-200 px-3 py-2 rounded-full hover:bg-gray-100"
                  >
                    {sugerencia}
                  </button>

                )
              )}

            </div>
          )}


          {/* ================================================== */}
          {/* GEMINI RESPONDIENDO */}
          {/* ================================================== */}

          {enviando && (

            <div className="flex gap-3">

              <div className="w-8 h-8 rounded-full bg-green-100 text-green-600 flex items-center justify-center shrink-0">
                <Bot size={16} />
              </div>

              <p className="text-xs text-gray-400 self-center">
                Analizando datos de CryoMetric...
              </p>

            </div>

          )}


          <div ref={bottomRef} />

        </div>


        {/* ==================================================== */}
        {/* INPUT */}
        {/* ==================================================== */}

        <div className="border-t border-gray-100 p-4">

          <form
            onSubmit={handleEnviar}
            className="flex items-center gap-3 bg-gray-50 border border-gray-200 rounded-xl px-4 py-2"
          >

            <button
              type="button"
              className="p-1.5 rounded-lg hover:bg-gray-200"
            >
              <Paperclip
                size={18}
                className="text-gray-500"
              />
            </button>


            <input
              type="text"
              value={pregunta}
              onChange={(e) =>
                setPregunta(e.target.value)
              }
              disabled={
                enviando ||
                !camaraId
              }
              placeholder={
                camaraId
                  ? 'Escribe tu consulta sobre la cámara seleccionada...'
                  : 'Selecciona una cámara para consultar a CryoBot'
              }
              className="flex-1 bg-transparent text-sm focus:outline-none disabled:opacity-50"
            />


            <button
              type="button"
              className="p-1.5 rounded-lg hover:bg-gray-200"
            >
              <Mic
                size={18}
                className="text-gray-500"
              />
            </button>


            <button
              type="submit"
              disabled={
                enviando ||
                !camaraId ||
                !pregunta.trim()
              }
              className="bg-green-600 hover:bg-green-700 text-white rounded-lg p-2 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <Send size={18} />
            </button>

          </form>

        </div>

      </div>


      {/* ====================================================== */}
      {/* FOOTER */}
      {/* ====================================================== */}

      <div className="flex items-center justify-between mt-3 text-xs text-gray-400">

        <span>
          El asistente puede cometer errores.
          Verifica los datos críticos.
        </span>

        <a
          href="#"
          className="text-green-600 hover:text-green-700 font-medium"
        >
          Ver Documentación de la API
        </a>

      </div>

    </div>
  );
};


export default ChatIAView;