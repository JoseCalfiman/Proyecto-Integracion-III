import logging
import os

from google import genai
from google.genai import types


logger = logging.getLogger(__name__)


GEMINI_MODEL = os.getenv(
    "GEMINI_MODEL",
    "gemini-3.8-flash",
)


class GeminiConfigurationError(RuntimeError):
    """La integración Gemini no está configurada correctamente."""


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
    )


def generar_respuesta(
    prompt: str,
    *,
    system_instruction: str | None = None,
) -> str:
    """
    Genera una respuesta de texto utilizando Gemini.
    """

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
                temperature=0.2,
            ),
        )

    except Exception as exc:
        logger.exception(
            "Error llamando a Gemini"
        )

        raise GeminiServiceError(
            "Gemini no respondió correctamente"
        ) from exc

    text = (
        response.text or ""
    ).strip()

    if not text:
        raise GeminiServiceError(
            "Gemini devolvió una respuesta vacía"
        )

    return text