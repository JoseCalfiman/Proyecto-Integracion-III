from datetime import datetime, timezone

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    status,
)

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from database import get_db

from gemini_client import (
    GEMINI_MODEL,
    GeminiConfigurationError,
    GeminiServiceError,
    generar_respuesta,
)

from gemini_context import (
    ChamberNotFoundError,
    construir_contexto_24h,
)

from models import (
    AiMessage,
    Conversation,
)

from schemas import (
    GeminiChatRequest,
    GeminiChatResponse,
)


router = APIRouter(
    prefix="/gemini",
    tags=["gemini"],
)


SYSTEM_INSTRUCTION = """
Eres CryoBot, el asistente inteligente de CryoMetric.

CryoMetric es una plataforma de monitoreo de cámaras
frigoríficas.

Debes responder siempre en español.

REGLAS OBLIGATORIAS:

1. Usa exclusivamente el contexto real proporcionado.

2. No inventes temperaturas, consumos, alertas ni eventos.

3. Si no existen datos suficientes para responder,
indícalo explícitamente.

4. No afirmes que existe una alerta si el contexto
no contiene una alerta.

5. Diferencia entre estado actual e información histórica.

6. Sé claro, breve y técnicamente preciso.

7. Si detectas condiciones preocupantes en los datos,
descríbelas sin inventar diagnósticos.
""".strip()


@router.post(
    "/chat",
    response_model=GeminiChatResponse,
)
def gemini_chat(
    data: GeminiChatRequest,
    db: Session = Depends(get_db),
):
    # CONTEXTO REAL DE CRYOMETRIC
    try:
        contexto, metadata = construir_contexto_24h(
            db=db,
            camara_id=data.camara_id,
        )

    except ChamberNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cámara no encontrada",
        ) from exc

    # CONVERSACIÓN EXISTENTE
    conversation = None

    if data.id_conversation is not None:

        conversation = db.get(
            Conversation,
            data.id_conversation,
        )

        if conversation is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Conversación no encontrada",
            )

        if conversation.id_chamber != data.camara_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    "La conversación no pertenece "
                    "a la cámara seleccionada"
                ),
            )
    # PROMPT
    prompt = f"""
DATOS REALES OBTENIDOS DESDE CRYOMETRIC:

{contexto}

PREGUNTA DEL USUARIO:

{data.pregunta}

Responde utilizando exclusivamente los datos
proporcionados anteriormente.
""".strip()
    # GEMINI

    try:
        respuesta = generar_respuesta(
            prompt,
            system_instruction=SYSTEM_INSTRUCTION,
        )

    except GeminiConfigurationError as exc:
        db.rollback()

        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Gemini no está configurado en el servidor",
        ) from exc

    except GeminiServiceError as exc:
        db.rollback()

        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="IA no disponible en este momento",
        ) from exc

    # PERSISTENCIA DE CONVERSACIÓN

    try:

        # Primera pregunta: crear conversación.
        if conversation is None:
            conversation = Conversation(
                id_user=None,
                id_chamber=data.camara_id,
            )

            db.add(conversation)

            # Obtiene id_conversation sin hacer commit todavía.
            db.flush()


        # Guardar pregunta del usuario.
        mensaje_usuario = AiMessage(
            id_conversation=conversation.id_conversation,
            sender="user",
            content=data.pregunta,
        )


        # Guardar respuesta real de Gemini.
        mensaje_asistente = AiMessage(
            id_conversation=conversation.id_conversation,
            sender="assistant",
            content=respuesta,
        )


        db.add(mensaje_usuario)
        db.add(mensaje_asistente)


        # Mantener actualizada la actividad.
        conversation.last_activity_date = (
            datetime.now(timezone.utc)
        )


        # Pregunta + respuesta se guardan juntas.
        db.commit()

        db.refresh(conversation)

    except SQLAlchemyError as exc:

        db.rollback()

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=(
                "No fue posible guardar "
                "la conversación"
            ),
        ) from exc


    # ========================================================
    # RESPONSE
    # ========================================================

    return GeminiChatResponse(
        respuesta=respuesta,
        camara_id=data.camara_id,
        id_conversation=conversation.id_conversation,
        modelo=GEMINI_MODEL,
        periodo_horas=metadata["periodo_horas"],
        mediciones_consideradas=(
            metadata["mediciones_consideradas"]
        ),
        alertas_consideradas=(
            metadata["alertas_consideradas"]
        ),
    )