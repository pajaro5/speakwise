import tempfile

import cmudict
import librosa
import numpy as np
import parselmouth

_cmu = cmudict.dict()


def load_waveform(audio: bytes) -> tuple[np.ndarray, int]:
    """Decodifica audio (webm/opus del navegador, o cualquier formato que
    ffmpeg entienda) a una señal mono + sample rate, vía librosa/audioread."""
    with tempfile.NamedTemporaryFile(suffix=".webm") as tmp:
        tmp.write(audio)
        tmp.flush()
        waveform, sr = librosa.load(tmp.name, sr=None, mono=True)
    return waveform, sr


def _vowels(word: str) -> list[str] | None:
    entries = _cmu.get(word.lower())
    if not entries:
        return None
    return [p for p in entries[0] if p[-1].isdigit()]


def expected_stress_syllable(word: str) -> int | None:
    """Índice (entre las vocales) de la sílaba con acento primario según
    CMU dict, o None si la palabra no está en el diccionario."""
    vowels = _vowels(word)
    if not vowels:
        return None
    for idx, v in enumerate(vowels):
        if v.endswith("1"):
            return idx
    return 0


def syllable_count(word: str) -> int | None:
    vowels = _vowels(word)
    return len(vowels) if vowels else None


def detect_stress_syllable(
    waveform: np.ndarray, sr: int, start: float, end: float, syllables: int
) -> int:
    """Divide [start, end] en `syllables` partes iguales y devuelve el
    índice de la parte con mayor pico de intensidad — un proxy simple de
    sílaba tónica que no requiere alineación fonémica real.

    Usa el pico (no el promedio) porque el promedio por segmento se diluye
    con el ataque de la consonante inicial de cada sílaba, sesgando hacia
    sílabas "sin consonante inicial" independientemente del acento real
    (encontrado probando en vivo contra audio TTS real). Es una heurística
    de mínimo esfuerzo, no alineación fonémica de verdad — su precisión
    real contra voz humana está pendiente de EVAL-01.
    """
    sound = parselmouth.Sound(waveform, sampling_frequency=sr)
    duration = end - start
    step = duration / syllables
    peaks = []
    for i in range(syllables):
        seg_start = max(start + i * step, sound.xmin)
        seg_end = min(start + (i + 1) * step, sound.xmax)
        segment = sound.extract_part(from_time=seg_start, to_time=seg_end)
        intensity = segment.to_intensity()
        values = intensity.values[~np.isnan(intensity.values)]
        peaks.append(float(values.max()) if values.size else float("-inf"))
    return int(np.argmax(peaks))


def analyze_stress(
    waveform: np.ndarray, sr: int, words: list[dict], target_words: list[str]
) -> list[dict]:
    """Compara, para cada palabra objetivo que aparece en la transcripción,
    la sílaba tónica esperada (CMU dict) contra la detectada acústicamente.
    Ignora palabras monosílabas o fuera del diccionario (no aplica LFC)."""
    target_lower = {w.lower() for w in target_words}
    results = []
    for w in words:
        word_text = w["w"].strip(".,!?").lower()
        if word_text not in target_lower:
            continue
        expected = expected_stress_syllable(word_text)
        syllables = syllable_count(word_text)
        if expected is None or not syllables or syllables < 2:
            continue
        detected = detect_stress_syllable(waveform, sr, w["start"], w["end"], syllables)
        results.append(
            {
                "word": word_text,
                "expected_syl": expected,
                "detected_syl": detected,
                "correct": detected == expected,
            }
        )
    return results
