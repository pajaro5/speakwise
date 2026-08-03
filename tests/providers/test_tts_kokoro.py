import io

import numpy as np
import pytest
import soundfile as sf

from backend.providers import tts_kokoro
from backend.providers.tts_kokoro import KokoroTTSProvider
from backend.services.exceptions import ProviderUnavailableError


class _FakePipeline:
    def __call__(self, text: str, voice: str):
        audio = np.zeros(240, dtype=np.float32)  # 10ms de silencio a 24kHz
        yield ("graphemes", "phonemes", audio)


class _BrokenPipeline:
    def __call__(self, text: str, voice: str):
        raise RuntimeError("model failed to load")


@pytest.mark.asyncio
async def test_synthesize_returns_valid_wav_bytes(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(tts_kokoro, "_get_pipeline", lambda lang_code="a": _FakePipeline())
    provider = KokoroTTSProvider()

    result = await provider.synthesize("hello there")

    assert isinstance(result, bytes)
    assert len(result) > 0
    data, samplerate = sf.read(io.BytesIO(result))
    assert samplerate == 24000
    assert len(data) == 240


@pytest.mark.asyncio
async def test_synthesize_raises_domain_error_when_model_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(tts_kokoro, "_get_pipeline", lambda lang_code="a": _BrokenPipeline())
    provider = KokoroTTSProvider()

    with pytest.raises(ProviderUnavailableError):
        await provider.synthesize("hello there")
