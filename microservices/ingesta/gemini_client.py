import logging
import os

from google import genai
from google.genai import types

logger = logging.getLogger(__name__)

GEMINI_MODEL = os.getenv(
    "GEMINI_MODEL",
    "gemini-3.8-flash",
)


GEMINI_TIMEOUT_MS = int(
    os.getenv("GEMINI_TIMEOUT_MS", "8000")
)

GEMINI_MAX_ATTEMPTS = int(
    os.getenv("GEMINI_MAX_ATTEMPTS", "1")
)


class GeminiConfigurationError(RuntimeError):
    """Gemini no está configurado correctamente."""


class GeminiServiceError(RuntimeError):
    """Gemini no pudo generar una respuesta utilizable."""


def _get_client() -> genai.Client:
    api_key = os.getenv(
        "GEMINI_API_KEY",
        "",
    ).strip()

    if not api_key:
        raise GeminiConfigurationError(
            "GEMINI_API_KEY no está configurada"
        )

    return genai.Client(
        api_key=api_key,
        http_options=types.HttpOptions(
            timeout=GEMINI_TIMEOUT_MS,
            retry_options=types.HttpRetryOptions(
                attempts=GEMINI_MAX_ATTEMPTS,
            ),
        ),
    )


def generar_respuesta(
    prompt: str,
    *,
    system_instruction: str | None = None,
) -> str:

    if not prompt or not prompt.strip():
        raise ValueError(
            "El prompt no puede estar vacío"
        )

    client = _get_client()

    try:
        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=prompt.strip(),
            config=types.GenerateContentConfig(
                system_instruction=system_instruction,
            ),
        )

    except Exception as exc:
        # No imprimimos el mensaje completo de la excepción
        # para evitar filtrar credenciales en logs.
        logger.error(
            "Error Gemini: %s",
            type(exc).__name__,
        )

        raise GeminiServiceError(
            "Gemini no respondió correctamente"
        ) from exc

    text = (response.text or "").strip()

    if not text:
        raise GeminiServiceError(
            "Gemini devolvió una respuesta vacía"
        )

    return text