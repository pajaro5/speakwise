import pytest

from backend.providers.base import LLMProvider, STTProvider, TTSProvider, Transcript


def test_stt_provider_cannot_be_instantiated_directly() -> None:
    with pytest.raises(TypeError):
        STTProvider()  # type: ignore[abstract]


def test_tts_provider_cannot_be_instantiated_directly() -> None:
    with pytest.raises(TypeError):
        TTSProvider()  # type: ignore[abstract]


def test_llm_provider_cannot_be_instantiated_directly() -> None:
    with pytest.raises(TypeError):
        LLMProvider()  # type: ignore[abstract]


def test_incomplete_subclass_cannot_be_instantiated() -> None:
    class IncompleteSTT(STTProvider):
        pass

    with pytest.raises(TypeError):
        IncompleteSTT()  # type: ignore[abstract]


@pytest.mark.asyncio
async def test_complete_subclass_can_be_instantiated_and_used() -> None:
    class FakeSTT(STTProvider):
        async def transcribe(self, audio: bytes) -> Transcript:
            return Transcript(text="hello", wpm=90.0)

    provider = FakeSTT()
    result = await provider.transcribe(b"fake-audio")

    assert result.text == "hello"
    assert result.wpm == 90.0
    assert result.words == []
    assert result.fillers == 0


def test_transcript_defaults() -> None:
    t = Transcript(text="hi", wpm=100.0)

    assert t.words == []
    assert t.phonemes == []
    assert t.fillers == 0
