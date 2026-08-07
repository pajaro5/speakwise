import json

from backend.providers.base import LLMProvider
from backend.services.exceptions import ProviderUnavailableError

# Fase C del plan de mejora (comparación vs Loora): los 30 modismos
# curados de chunks.csv son fijos — esto complementa esa rotación con
# vocabulario que nace de lo que el alumno realmente quiere decir en el
# momento, en vez de esperar a que rote un ítem prearmado.
SYSTEM_PROMPT = (
    "Sos un traductor y coach de inglés conversacional para hispanohablantes. "
    "Dada una frase en español que el alumno quiere decir en inglés, respondé "
    "con la traducción más natural y conversacional (no literal palabra por "
    "palabra) que usaría un hablante nativo, más una nota breve EN ESPAÑOL "
    "sobre cómo/cuándo usarla si hace falta alguna aclaración (registro, "
    "contexto, uso informal vs. formal). Si no hace falta ninguna aclaración, "
    "dejá notes vacío. Respondé ÚNICAMENTE con JSON válido de la forma "
    '{"english": "...", "notes": "..."}, sin texto adicional. El campo '
    '"english" tiene que estar TOTALMENTE en inglés.'
)


async def get_translation_practice(llm: LLMProvider, *, spanish_text: str) -> dict:
    raw = await llm.complete(
        messages=[{"role": "user", "content": spanish_text}],
        system=SYSTEM_PROMPT,
    )
    try:
        result = json.loads(raw)
    except (json.JSONDecodeError, TypeError) as exc:
        raise ProviderUnavailableError(
            f"El LLM no devolvió JSON válido para la traducción: {raw!r}"
        ) from exc

    if not result.get("english"):
        raise ProviderUnavailableError("Falta 'english' en la traducción generada")

    return {"english": result["english"], "notes": result.get("notes", "")}
