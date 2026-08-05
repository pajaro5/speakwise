from backend.providers.base import STTProvider, Transcript
from backend.providers.factory import get_stt_provider
from backend.services.stress import analyze_stress, load_waveform

FILLER_WORDS = {"um", "uh", "eh", "er", "ah", "hmm"}


def _clean_word(word: str) -> str:
    return word.strip(".,!?¿¡").lower()


def _count_fillers(words: list[dict]) -> int:
    return sum(1 for w in words if _clean_word(w["w"]) in FILLER_WORDS)


def _compute_wpm(words: list[dict]) -> float:
    if len(words) < 2:
        return 0.0
    duration_min = (words[-1]["end"] - words[0]["start"]) / 60.0
    if duration_min <= 0:
        return 0.0
    return len(words) / duration_min


async def transcribe_and_analyze(
    audio: bytes,
    provider: STTProvider | None = None,
    target_words: list[str] | None = None,
) -> Transcript:
    """Transcribe audio y calcula wpm/fillers, y opcionalmente stress_results.

    El provider de STT devuelve texto + timestamps crudos (ver DESIGN.md §10);
    wpm/fillers se calculan acá, no en el provider, para no romper la regla de
    dependencias de CODING_STANDARDS.md §2 (providers nunca importa services).

    `target_words` (ITER-2): si se pasan, se analiza la sílaba tónica de esas
    palabras contra lo que dijo el alumno (módulo de práctica de patrones).
    Sin target_words no se toca el audio para esto — evita costo innecesario
    en /api/transcribe de conversación libre.
    """
    stt = provider or get_stt_provider()
    raw = await stt.transcribe(audio)

    stress_results: list[dict] = []
    if target_words:
        waveform, sr = load_waveform(audio)
        stress_results = analyze_stress(waveform, sr, raw.words, target_words)

    return Transcript(
        text=raw.text,
        wpm=_compute_wpm(raw.words),
        words=raw.words,
        phonemes=raw.phonemes,
        fillers=_count_fillers(raw.words),
        stress_results=stress_results,
    )
