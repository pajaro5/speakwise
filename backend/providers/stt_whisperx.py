import asyncio
import tempfile
from concurrent.futures import ThreadPoolExecutor

from faster_whisper import WhisperModel

from backend.providers.base import STTProvider, Transcript
from backend.services.exceptions import ProviderUnavailableError

_executor = ThreadPoolExecutor(max_workers=2)
_model_cache: dict[str, WhisperModel] = {}


def _get_model(model_size: str) -> WhisperModel:
    if model_size not in _model_cache:
        _model_cache[model_size] = WhisperModel(
            model_size, device="cpu", compute_type="int8"
        )
    return _model_cache[model_size]


def _transcribe_sync(model: WhisperModel, audio_path: str) -> tuple[str, list[dict]]:
    # language="en" fijo: la app es exclusivamente de inglés — sin esto,
    # Whisper adivina el idioma desde el audio y en grabaciones cortas
    # (4s en módulo 1) a veces le erra feo (ej. transcribe en griego).
    segments, _info = model.transcribe(audio_path, word_timestamps=True, language="en")
    text_parts: list[str] = []
    words: list[dict] = []
    for segment in segments:
        text_parts.append(segment.text)
        for word in segment.words or []:
            words.append({"w": word.word.strip(), "start": word.start, "end": word.end})
    return "".join(text_parts).strip(), words


class WhisperXLocalProvider(STTProvider):
    """STT local vía faster-whisper (MIT). Software libre — provider por defecto."""

    def __init__(self, model_size: str = "base") -> None:
        self._model_size = model_size

    async def transcribe(self, audio: bytes) -> Transcript:
        with tempfile.NamedTemporaryFile(suffix=".webm", delete=True) as tmp:
            tmp.write(audio)
            tmp.flush()
            try:
                model = _get_model(self._model_size)
                loop = asyncio.get_running_loop()
                text, words = await loop.run_in_executor(
                    _executor, _transcribe_sync, model, tmp.name
                )
            except Exception as exc:
                raise ProviderUnavailableError(
                    f"Whisper local no disponible: {exc}"
                ) from exc
        # wpm/fillers los calcula services/acoustic.py a partir de `words`, no el provider.
        return Transcript(text=text, wpm=0.0, words=words)
