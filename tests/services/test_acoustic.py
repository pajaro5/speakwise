import pytest

from backend.providers.base import STTProvider, Transcript
from backend.services.acoustic import _compute_wpm, _count_fillers, transcribe_and_analyze


class _FakeSTTProvider(STTProvider):
    def __init__(self, transcript: Transcript) -> None:
        self._transcript = transcript

    async def transcribe(self, audio: bytes) -> Transcript:
        return self._transcript


def test_compute_wpm_matches_manual_calculation() -> None:
    # 10 palabras entre t=0.0 y t=5.9s -> ~10 / (5.9/60) ~= 101.7 wpm
    words = [{"w": f"word{i}", "start": i * 0.6, "end": i * 0.6 + 0.5} for i in range(10)]

    wpm = _compute_wpm(words)

    assert wpm == pytest.approx(101.7, rel=0.02)


def test_compute_wpm_zero_for_single_word() -> None:
    assert _compute_wpm([{"w": "hi", "start": 0.0, "end": 0.3}]) == 0.0


def test_compute_wpm_zero_for_no_words() -> None:
    assert _compute_wpm([]) == 0.0


def test_count_fillers_detects_common_filler_words() -> None:
    words = [
        {"w": "I", "start": 0.0, "end": 0.1},
        {"w": "um,", "start": 0.1, "end": 0.3},
        {"w": "think", "start": 0.3, "end": 0.5},
        {"w": "uh", "start": 0.5, "end": 0.7},
        {"w": "that's", "start": 0.7, "end": 0.9},
        {"w": "right", "start": 0.9, "end": 1.1},
    ]

    assert _count_fillers(words) == 2


def test_count_fillers_zero_when_none_present() -> None:
    words = [
        {"w": "hello", "start": 0.0, "end": 0.3},
        {"w": "world", "start": 0.3, "end": 0.6},
    ]

    assert _count_fillers(words) == 0


def test_count_fillers_is_case_insensitive() -> None:
    words = [{"w": "Um", "start": 0.0, "end": 0.2}, {"w": "UH", "start": 0.2, "end": 0.4}]

    assert _count_fillers(words) == 2


@pytest.mark.asyncio
async def test_transcribe_and_analyze_computes_wpm_and_fillers_from_provider_output() -> None:
    raw_words = [
        {"w": "I", "start": 0.0, "end": 0.2},
        {"w": "um", "start": 0.2, "end": 0.4},
        {"w": "go", "start": 0.4, "end": 3.6},
    ]
    fake_transcript = Transcript(text="I um go", wpm=0.0, words=raw_words, fillers=0)
    provider = _FakeSTTProvider(fake_transcript)

    result = await transcribe_and_analyze(b"fake-webm-audio", provider=provider)

    assert result.text == "I um go"
    assert result.words == raw_words
    assert result.fillers == 1
    assert result.wpm > 0


@pytest.mark.asyncio
async def test_transcribe_and_analyze_handles_empty_transcription() -> None:
    fake_transcript = Transcript(text="", wpm=0.0, words=[], fillers=0)
    provider = _FakeSTTProvider(fake_transcript)

    result = await transcribe_and_analyze(b"silence.webm", provider=provider)

    assert result.text == ""
    assert result.wpm == 0.0
    assert result.fillers == 0


@pytest.mark.asyncio
async def test_transcribe_and_analyze_uses_factory_provider_by_default(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_transcript = Transcript(text="hello", wpm=0.0, words=[], fillers=0)
    provider = _FakeSTTProvider(fake_transcript)
    monkeypatch.setattr(
        "backend.services.acoustic.get_stt_provider", lambda: provider
    )

    result = await transcribe_and_analyze(b"fake-audio")

    assert result.text == "hello"
