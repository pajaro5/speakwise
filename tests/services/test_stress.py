import subprocess

import numpy as np
import pytest
import soundfile as sf

from backend.services.stress import (
    analyze_stress,
    detect_stress_syllable,
    expected_stress_syllable,
    load_waveform,
    syllable_count,
)


def test_expected_stress_syllable_known_word() -> None:
    assert expected_stress_syllable("average") == 0


def test_expected_stress_syllable_second_syllable() -> None:
    assert expected_stress_syllable("about") == 1


def test_expected_stress_syllable_unknown_word_returns_none() -> None:
    assert expected_stress_syllable("zzznotaword") is None


def test_syllable_count_known_word() -> None:
    assert syllable_count("average") == 3
    assert syllable_count("about") == 2


def _two_syllable_wave(sr: int, loud_half: int) -> np.ndarray:
    """1 segundo de audio dividido en 2 mitades: una fuerte (amplitud 0.8),
    la otra floja (amplitud 0.02), para simular qué mitad tiene la sílaba
    tónica sin depender de una grabación real."""
    t = np.linspace(0, 1.0, sr, endpoint=False)
    tone = np.sin(2 * np.pi * 200 * t)
    half = sr // 2
    wave = np.zeros_like(tone)
    loud_amp, quiet_amp = 0.8, 0.02
    if loud_half == 0:
        wave[:half] = tone[:half] * loud_amp
        wave[half:] = tone[half:] * quiet_amp
    else:
        wave[:half] = tone[:half] * quiet_amp
        wave[half:] = tone[half:] * loud_amp
    return wave.astype(np.float32)


def test_detect_stress_syllable_picks_loudest_segment_first_half() -> None:
    sr = 16000
    wave = _two_syllable_wave(sr, loud_half=0)

    detected = detect_stress_syllable(wave, sr, start=0.0, end=1.0, syllables=2)

    assert detected == 0


def test_detect_stress_syllable_picks_loudest_segment_second_half() -> None:
    sr = 16000
    wave = _two_syllable_wave(sr, loud_half=1)

    detected = detect_stress_syllable(wave, sr, start=0.0, end=1.0, syllables=2)

    assert detected == 1


def test_analyze_stress_marks_correct_when_stress_matches() -> None:
    """"about" tiene la tónica en la 2da sílaba (índice 1) según CMU dict."""
    sr = 16000
    wave = _two_syllable_wave(sr, loud_half=1)
    words = [{"w": "about", "start": 0.0, "end": 1.0}]

    results = analyze_stress(wave, sr, words, target_words=["about"])

    assert results == [
        {"word": "about", "expected_syl": 1, "detected_syl": 1, "correct": True}
    ]


def test_analyze_stress_marks_incorrect_when_stress_does_not_match() -> None:
    sr = 16000
    wave = _two_syllable_wave(sr, loud_half=0)  # el alumno acentuó la 1ra, no la 2da
    words = [{"w": "about", "start": 0.0, "end": 1.0}]

    results = analyze_stress(wave, sr, words, target_words=["about"])

    assert results == [
        {"word": "about", "expected_syl": 1, "detected_syl": 0, "correct": False}
    ]


def test_analyze_stress_ignores_words_not_in_target_list() -> None:
    sr = 16000
    wave = _two_syllable_wave(sr, loud_half=0)
    words = [{"w": "hello", "start": 0.0, "end": 1.0}]

    results = analyze_stress(wave, sr, words, target_words=["about"])

    assert results == []


def test_load_waveform_decodes_real_webm_audio(tmp_path) -> None:
    """El navegador manda audio webm/opus (MediaRecorder), no WAV — el
    loader tiene que poder decodificarlo de verdad, no solo WAV crudo."""
    sr = 16000
    t = np.linspace(0, 1.0, sr, endpoint=False)
    tone = (np.sin(2 * np.pi * 200 * t) * 0.5).astype(np.float32)
    wav_path = tmp_path / "tone.wav"
    webm_path = tmp_path / "tone.webm"
    sf.write(wav_path, tone, sr)
    subprocess.run(
        ["ffmpeg", "-y", "-i", str(wav_path), "-c:a", "libopus", str(webm_path)],
        check=True, capture_output=True,
    )
    webm_bytes = webm_path.read_bytes()

    waveform, loaded_sr = load_waveform(webm_bytes)

    assert loaded_sr > 0
    assert len(waveform) > 0
    assert abs(len(waveform) / loaded_sr - 1.0) < 0.2


def test_analyze_stress_skips_monosyllabic_words() -> None:
    sr = 16000
    wave = _two_syllable_wave(sr, loud_half=0)
    words = [{"w": "cat", "start": 0.0, "end": 1.0}]

    results = analyze_stress(wave, sr, words, target_words=["cat"])

    assert results == []
