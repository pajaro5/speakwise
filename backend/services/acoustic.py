from backend.providers.base import STTProvider, Transcript
from backend.providers.factory import get_stt_provider

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
    audio: bytes, provider: STTProvider | None = None
) -> Transcript:
    """Transcribe audio y calcula wpm/fillers.

    El provider de STT devuelve texto + timestamps crudos (ver DESIGN.md §10);
    wpm/fillers se calculan acá, no en el provider, para no romper la regla de
    dependencias de CODING_STANDARDS.md §2 (providers nunca importa services).
    """
    stt = provider or get_stt_provider()
    raw = await stt.transcribe(audio)
    return Transcript(
        text=raw.text,
        wpm=_compute_wpm(raw.words),
        words=raw.words,
        phonemes=raw.phonemes,
        fillers=_count_fillers(raw.words),
    )
