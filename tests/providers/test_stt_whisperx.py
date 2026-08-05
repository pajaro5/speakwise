import pytest

from backend.providers import stt_whisperx
from backend.providers.stt_whisperx import WhisperXLocalProvider
from backend.services.exceptions import ProviderUnavailableError


class _FakeWord:
    def __init__(self, word: str, start: float, end: float) -> None:
        self.word = word
        self.start = start
        self.end = end


class _FakeSegment:
    def __init__(self, text: str, words: list[_FakeWord]) -> None:
        self.text = text
        self.words = words


class _FakeModel:
    def __init__(self) -> None:
        self.last_kwargs: dict = {}

    def transcribe(self, audio_path: str, **kwargs):
        self.last_kwargs = kwargs
        segments = [
            _FakeSegment(
                " hello world",
                [_FakeWord("hello", 0.0, 0.4), _FakeWord("world", 0.5, 0.9)],
            )
        ]
        return segments, object()


class _BrokenModel:
    def transcribe(self, audio_path: str, word_timestamps: bool = True):
        raise RuntimeError("model failed to load")


@pytest.mark.asyncio
async def test_transcribe_returns_text_and_words(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(stt_whisperx, "_get_model", lambda size: _FakeModel())
    provider = WhisperXLocalProvider(model_size="base")

    result = await provider.transcribe(b"fake-webm-bytes")

    assert result.text == "hello world"
    assert result.words == [
        {"w": "hello", "start": 0.0, "end": 0.4},
        {"w": "world", "start": 0.5, "end": 0.9},
    ]
    assert result.wpm == 0.0


@pytest.mark.asyncio
async def test_transcribe_pins_language_to_english(monkeypatch: pytest.MonkeyPatch) -> None:
    """Reportado por el usuario: sin fijar el idioma, Whisper adivina el
    idioma hablado a partir del audio — en grabaciones cortas (4s, módulo 1)
    a veces le erra feo y devuelve texto en otro alfabeto (ej. griego). Esta
    app es exclusivamente de inglés, no hay nada que adivinar."""
    fake_model = _FakeModel()
    monkeypatch.setattr(stt_whisperx, "_get_model", lambda size: fake_model)
    provider = WhisperXLocalProvider(model_size="base")

    await provider.transcribe(b"fake-webm-bytes")

    assert fake_model.last_kwargs.get("language") == "en"


@pytest.mark.asyncio
async def test_transcribe_raises_domain_error_on_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(stt_whisperx, "_get_model", lambda size: _BrokenModel())
    provider = WhisperXLocalProvider(model_size="base")

    with pytest.raises(ProviderUnavailableError):
        await provider.transcribe(b"fake-webm-bytes")
