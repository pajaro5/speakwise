import numpy as np
import pytest

from backend.services.phoneme import (
    analyze_phonemes,
    arpabet_to_ipa,
    count_words_evaluated,
    expected_focus_phoneme,
)


def test_arpabet_to_ipa_common_vowels() -> None:
    assert arpabet_to_ipa("AE1") == "æ"
    assert arpabet_to_ipa("IY0") == "i"
    assert arpabet_to_ipa("EY1") == "eɪ"


def test_arpabet_to_ipa_ah_is_schwa_when_unstressed() -> None:
    assert arpabet_to_ipa("AH0") == "ə"
    assert arpabet_to_ipa("AH1") == "ʌ"


def test_arpabet_to_ipa_er_is_schwa_when_unstressed() -> None:
    assert arpabet_to_ipa("ER0") == "ɚ"
    assert arpabet_to_ipa("ER1") == "ɝ"


def test_arpabet_to_ipa_unknown_phoneme_returns_none() -> None:
    assert arpabet_to_ipa("ZZ9") is None


def test_expected_focus_phoneme_known_word() -> None:
    assert expected_focus_phoneme("average") == ("AE1", "æ")


def test_expected_focus_phoneme_unknown_word_returns_none() -> None:
    assert expected_focus_phoneme("zzznotaword") is None


def test_analyze_phonemes_no_error_when_expected_phoneme_produced(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "backend.services.phoneme.recognize_phonemes",
        lambda waveform, sr, start, end: ["æ", "v", "ɚ", "ɹ", "ɪ", "dʒ"],
    )
    words = [{"w": "average", "start": 0.0, "end": 1.0}]

    errors = analyze_phonemes(np.zeros(16000), 16000, words, target_words=["average"])

    assert errors == []


def test_analyze_phonemes_reports_error_when_expected_phoneme_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "backend.services.phoneme.recognize_phonemes",
        lambda waveform, sr, start, end: ["b", "ə", "n", "a", "n", "a"],
    )
    words = [{"w": "banana", "start": 0.0, "end": 1.0}]

    errors = analyze_phonemes(np.zeros(16000), 16000, words, target_words=["banana"])

    assert errors == [{"word": "banana", "expected": "AE1", "produced": "b ə n a n a"}]


def test_analyze_phonemes_ignores_words_not_in_target_list(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "backend.services.phoneme.recognize_phonemes",
        lambda waveform, sr, start, end: ["h", "ɛ", "l", "oʊ"],
    )
    words = [{"w": "hello", "start": 0.0, "end": 1.0}]

    errors = analyze_phonemes(np.zeros(16000), 16000, words, target_words=["average"])

    assert errors == []


def test_count_words_evaluated_counts_target_words_found_in_transcript() -> None:
    """Necesario para poder calcular accuracy incluso en palabras monosílabas
    (analyze_stress las ignora — no hay contraste de sílaba tónica que
    marcar), reportado por el usuario: el patrón "letras mudas kn-/wr-"
    (know, knee, write, wrong, knife, todas monosílabas) nunca generaba
    stress_results, así que su accuracy se quedaba congelada en 0.0 para
    siempre y el patrón dominaba la selección de "menos practicado"."""
    words = [{"w": "know", "start": 0.0, "end": 0.5}, {"w": "knee", "start": 0.5, "end": 1.0}]

    count = count_words_evaluated(words, target_words=["know", "knee", "write", "wrong", "knife"])

    assert count == 2


def test_count_words_evaluated_ignores_words_not_in_target_list() -> None:
    words = [{"w": "hello", "start": 0.0, "end": 0.5}]

    count = count_words_evaluated(words, target_words=["know"])

    assert count == 0


def test_count_words_evaluated_ignores_words_not_in_cmu_dict() -> None:
    words = [{"w": "zzznotaword", "start": 0.0, "end": 0.5}]

    count = count_words_evaluated(words, target_words=["zzznotaword"])

    assert count == 0


@pytest.mark.integration
def test_recognize_phonemes_against_real_tts_audio() -> None:
    """Contra el modelo real (wav2vec2-lv-60-espeak-cv-ft, ~315M parámetros,
    se descarga la primera vez) y audio real generado por el TTS de la app.
    Excluido del run por defecto — mismo patrón que los tests de Kokoro."""
    import asyncio

    from backend.providers.factory import get_tts_provider
    from backend.services.phoneme import recognize_phonemes
    from backend.services.stress import load_waveform

    async def _get_audio() -> bytes:
        tts = get_tts_provider()
        return await tts.synthesize("average")

    audio = asyncio.run(_get_audio())
    waveform, sr = load_waveform(audio)

    phonemes = recognize_phonemes(waveform, sr, 0.0, len(waveform) / sr)

    assert "æ" in phonemes
