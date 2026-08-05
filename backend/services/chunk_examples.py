import json

from backend.providers.base import LLMProvider
from backend.services.exceptions import ProviderUnavailableError

SYSTEM_PROMPT = (
    "Sos un generador de ejemplos de uso en inglés para un chunk (frase corta) que "
    "un estudiante hispanohablante está aprendiendo. Dado el chunk y su función "
    "gramatical, generá 3 ejemplos de uso EN INGLÉS: 1) una oración simple que use el "
    "chunk, 2) un párrafo corto (2-3 oraciones) que lo use naturalmente en contexto, "
    "3) un mini-diálogo de 2-4 líneas (formato 'A: ...' / 'B: ...') donde una línea use "
    "el chunk. Respondé ÚNICAMENTE con JSON válido de la forma "
    '{"sentence": "...", "paragraph": "...", "conversation": "..."}, sin texto adicional.'
)

REQUIRED_KEYS = ("sentence", "paragraph", "conversation")


async def get_chunk_examples(llm: LLMProvider, *, chunk: str, function: str) -> dict:
    raw = await llm.complete(
        messages=[{"role": "user", "content": f'Chunk: "{chunk}"\nFunción: {function}'}],
        system=SYSTEM_PROMPT,
    )
    try:
        examples = json.loads(raw)
    except (json.JSONDecodeError, TypeError) as exc:
        raise ProviderUnavailableError(
            f"El LLM no devolvió JSON válido para los ejemplos del chunk: {raw!r}"
        ) from exc

    for key in REQUIRED_KEYS:
        if not examples.get(key):
            raise ProviderUnavailableError(
                f"Falta '{key}' en los ejemplos generados para el chunk"
            )

    return {key: examples[key] for key in REQUIRED_KEYS}
