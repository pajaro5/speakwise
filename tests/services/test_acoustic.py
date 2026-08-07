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
async def test_transcribe_and_analyze_computes_stress_results_when_target_words_given(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    raw_words = [{"w": "average", "start": 0.0, "end": 1.0}]
    fake_transcript = Transcript(text="average", wpm=0.0, words=raw_words, fillers=0)
    provider = _FakeSTTProvider(fake_transcript)

    monkeypatch.setattr(
        "backend.services.acoustic.load_waveform", lambda audio: ("FAKE_WAVE", 16000)
    )
    monkeypatch.setattr(
        "backend.services.acoustic.analyze_stress",
        lambda waveform, sr, words, target_words: [
            {"word": "average", "expected_syl": 0, "detected_syl": 0, "correct": True}
        ],
    )
    monkeypatch.setattr(
        "backend.services.acoustic.analyze_phonemes", lambda waveform, sr, words, target_words: []
    )

    result = await transcribe_and_analyze(
        b"fake-webm-audio", provider=provider, target_words=["average"]
    )

    assert result.stress_results == [
        {"word": "average", "expected_syl": 0, "detected_syl": 0, "correct": True}
    ]


@pytest.mark.asyncio
async def test_transcribe_and_analyze_computes_phoneme_errors_when_target_words_given(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    raw_words = [{"w": "banana", "start": 0.0, "end": 1.0}]
    fake_transcript = Transcript(text="banana", wpm=0.0, words=raw_words, fillers=0)
    provider = _FakeSTTProvider(fake_transcript)

    monkeypatch.setattr(
        "backend.services.acoustic.load_waveform", lambda audio: ("FAKE_WAVE", 16000)
    )
    monkeypatch.setattr(
        "backend.services.acoustic.analyze_stress", lambda waveform, sr, words, target_words: []
    )
    monkeypatch.setattr(
        "backend.services.acoustic.analyze_phonemes",
        lambda waveform, sr, words, target_words: [
            {"word": "banana", "expected": "AE1", "produced": "b ə n a n a"}
        ],
    )

    result = await transcribe_and_analyze(
        b"fake-webm-audio", provider=provider, target_words=["banana"]
    )

    assert result.phoneme_errors == [
        {"word": "banana", "expected": "AE1", "produced": "b ə n a n a"}
    ]


@pytest.mark.asyncio
async def test_transcribe_and_analyze_computes_phoneme_evaluated_count(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Reportado por el usuario: el patrón "letras mudas kn-/wr-" (todas
    monosílabas) siempre le mostraba los mismos ejercicios — analyze_stress
    ignora monosílabas, así que stress_results siempre quedaba vacío y
    pattern_progress.accuracy se congelaba en 0.0 para siempre. phoneme_
    evaluated (independiente del número de sílabas) permite calcular
    accuracy real igual para esos patrones (ver test_log.py)."""
    raw_words = [{"w": "know", "start": 0.0, "end": 0.5}, {"w": "knee", "start": 0.5, "end": 1.0}]
    fake_transcript = Transcript(text="know knee", wpm=0.0, words=raw_words, fillers=0)
    provider = _FakeSTTProvider(fake_transcript)

    monkeypatch.setattr(
        "backend.services.acoustic.load_waveform", lambda audio: ("FAKE_WAVE", 16000)
    )
    monkeypatch.setattr(
        "backend.services.acoustic.analyze_stress", lambda waveform, sr, words, target_words: []
    )
    monkeypatch.setattr(
        "backend.services.acoustic.analyze_phonemes", lambda waveform, sr, words, target_words: []
    )

    result = await transcribe_and_analyze(
        b"fake-webm-audio", provider=provider, target_words=["know", "knee", "write"]
    )

    assert result.phoneme_evaluated == 2


@pytest.mark.asyncio
async def test_transcribe_and_analyze_groups_errors_by_pattern_name(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """DoD de BACKLOG.md: "si produzco 3+ errores de -age/-idge, pattern_errors
    lo reporta" — cuenta palabras únicas con error (stress o fonema), agrupadas
    bajo el nombre del patrón que se está practicando."""
    raw_words = [
        {"w": "average", "start": 0.0, "end": 1.0},
        {"w": "manage", "start": 1.0, "end": 2.0},
    ]
    fake_transcript = Transcript(text="average manage", wpm=0.0, words=raw_words, fillers=0)
    provider = _FakeSTTProvider(fake_transcript)

    monkeypatch.setattr(
        "backend.services.acoustic.load_waveform", lambda audio: ("FAKE_WAVE", 16000)
    )
    monkeypatch.setattr(
        "backend.services.acoustic.analyze_stress",
        lambda waveform, sr, words, target_words: [
            {"word": "average", "expected_syl": 0, "detected_syl": 1, "correct": False},
            {"word": "manage", "expected_syl": 0, "detected_syl": 0, "correct": True},
        ],
    )
    monkeypatch.setattr(
        "backend.services.acoustic.analyze_phonemes",
        lambda waveform, sr, words, target_words: [
            {"word": "manage", "expected": "AE1", "produced": "m ɛ n ɪ dʒ"}
        ],
    )

    result = await transcribe_and_analyze(
        b"fake-webm-audio",
        provider=provider,
        target_words=["average", "manage"],
        pattern_name="-age/-idge",
    )

    assert result.pattern_errors == {"-age/-idge": 2}


@pytest.mark.asyncio
async def test_transcribe_and_analyze_skips_pattern_errors_without_pattern_name(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    raw_words = [{"w": "average", "start": 0.0, "end": 1.0}]
    fake_transcript = Transcript(text="average", wpm=0.0, words=raw_words, fillers=0)
    provider = _FakeSTTProvider(fake_transcript)

    monkeypatch.setattr(
        "backend.services.acoustic.load_waveform", lambda audio: ("FAKE_WAVE", 16000)
    )
    monkeypatch.setattr(
        "backend.services.acoustic.analyze_stress",
        lambda waveform, sr, words, target_words: [
            {"word": "average", "expected_syl": 0, "detected_syl": 1, "correct": False}
        ],
    )
    monkeypatch.setattr(
        "backend.services.acoustic.analyze_phonemes", lambda waveform, sr, words, target_words: []
    )

    result = await transcribe_and_analyze(
        b"fake-webm-audio", provider=provider, target_words=["average"]
    )

    assert result.pattern_errors == {}


@pytest.mark.asyncio
async def test_transcribe_and_analyze_skips_stress_analysis_without_target_words() -> None:
    fake_transcript = Transcript(text="hello", wpm=0.0, words=[], fillers=0)
    provider = _FakeSTTProvider(fake_transcript)

    result = await transcribe_and_analyze(b"fake-audio", provider=provider)

    assert result.stress_results == []


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
