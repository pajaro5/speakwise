import asyncio
import io
from concurrent.futures import ThreadPoolExecutor

import numpy as np
import soundfile as sf
from kokoro import KPipeline

from backend.providers.base import TTSProvider
from backend.services.exceptions import ProviderUnavailableError

_executor = ThreadPoolExecutor(max_workers=2)
_pipeline_cache: dict[str, KPipeline] = {}

_SAMPLE_RATE = 24000
_DEFAULT_VOICE = "af_heart"


def _get_pipeline(lang_code: str = "a") -> KPipeline:
    if lang_code not in _pipeline_cache:
        _pipeline_cache[lang_code] = KPipeline(lang_code=lang_code)
    return _pipeline_cache[lang_code]


def _synthesize_sync(pipeline: KPipeline, text: str, voice: str) -> bytes:
    chunks: list[np.ndarray] = []
    for _graphemes, _phonemes, audio in pipeline(text, voice=voice):
        chunks.append(np.asarray(audio))
    full_audio = np.concatenate(chunks) if chunks else np.zeros(0, dtype=np.float32)

    buffer = io.BytesIO()
    sf.write(buffer, full_audio, _SAMPLE_RATE, format="WAV")
    return buffer.getvalue()


class KokoroTTSProvider(TTSProvider):
    """TTS local vía Kokoro-82M (Apache 2.0). Software libre — provider por defecto."""

    async def synthesize(self, text: str, voice: str = "default") -> bytes:
        voice_name = _DEFAULT_VOICE if voice == "default" else voice
        try:
            pipeline = _get_pipeline()
            loop = asyncio.get_running_loop()
            return await loop.run_in_executor(
                _executor, _synthesize_sync, pipeline, text, voice_name
            )
        except Exception as exc:
            raise ProviderUnavailableError(f"Kokoro no disponible: {exc}") from exc
