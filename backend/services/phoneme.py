import re

import cmudict
import numpy as np

_cmu = cmudict.dict()

# CMU ARPAbet -> IPA (General American). AH/ER dependen de si están
# acentuados (el modelo de fonemas distingue schwa vs. vocal plena).
_ARPABET_TO_IPA = {
    "AA": "ɑ", "AE": "æ", "AO": "ɔ", "AW": "aʊ", "AY": "aɪ",
    "B": "b", "CH": "tʃ", "D": "d", "DH": "ð", "EH": "ɛ",
    "EY": "eɪ", "F": "f", "G": "ɡ", "HH": "h", "IH": "ɪ",
    "IY": "i", "JH": "dʒ", "K": "k", "L": "l", "M": "m",
    "N": "n", "NG": "ŋ", "OW": "oʊ", "OY": "ɔɪ", "P": "p",
    "R": "ɹ", "S": "s", "SH": "ʃ", "T": "t", "TH": "θ",
    "UH": "ʊ", "UW": "u", "V": "v", "W": "w", "Y": "j",
    "Z": "z", "ZH": "ʒ",
}


def arpabet_to_ipa(phoneme: str) -> str | None:
    """Convierte un fonema ARPAbet (con o sin marca de stress) a IPA.

    AH/ER son casos especiales: átonos (stress 0) son schwa (ə/ɚ), con
    acento son la vocal plena (ʌ/ɝ) — coincide con lo que distingue el
    reconocedor de fonemas real (wav2vec2-espeak), no una simplificación."""
    stress = phoneme[-1] if phoneme and phoneme[-1].isdigit() else None
    base = re.sub(r"\d$", "", phoneme)
    if base == "AH":
        return "ə" if stress == "0" else "ʌ"
    if base == "ER":
        return "ɚ" if stress == "0" else "ɝ"
    return _ARPABET_TO_IPA.get(base)


# Fonema ARPAbet -> letras "de andar por casa" (no IPA) para una guía de
# pronunciación simple, tipo diccionario para no-lingüistas.
_ARPABET_TO_RESPELL = {
    "AA": "ah", "AE": "a", "AH": "uh", "AO": "aw", "AW": "ow", "AY": "eye",
    "B": "b", "CH": "ch", "D": "d", "DH": "th", "EH": "e", "ER": "er",
    "EY": "ay", "F": "f", "G": "g", "HH": "h", "IH": "i", "IY": "ee",
    "JH": "j", "K": "k", "L": "l", "M": "m", "N": "n", "NG": "ng",
    "OW": "oh", "OY": "oy", "P": "p", "R": "r", "S": "s", "SH": "sh",
    "T": "t", "TH": "th", "UH": "u", "UW": "oo", "V": "v", "W": "w",
    "Y": "y", "Z": "z", "ZH": "zh",
}


def _syllabify_phonemes(phonemes: list[str]) -> list[list[str]]:
    """Agrupa fonemas en sílabas por acentuación máxima del onset (cada
    consonante entre dos vocales se va con la sílaba SIGUIENTE) — no es
    syllabificación académica perfecta, pero es 100% consistente con
    expected_stress_syllable/syllable_count porque usa la misma secuencia
    de fonemas de CMU dict, no la ortografía (que no coincide de forma
    confiable — probado con una librería de hyphenation real antes de
    decidir esto)."""
    vowel_idx = [i for i, p in enumerate(phonemes) if p[-1].isdigit()]
    if not vowel_idx:
        return [phonemes]
    syllables = []
    boundary = 0
    for i, vi in enumerate(vowel_idx):
        if i == len(vowel_idx) - 1:
            syllables.append(phonemes[boundary:])
        else:
            syllables.append(phonemes[boundary : vi + 1])
            boundary = vi + 1
    return syllables


def simple_respelling(word: str) -> str | None:
    """Guía de pronunciación con letras comunes (no IPA), tipo diccionario
    para no-lingüistas — ej. "book" -> "buk". La sílaba con acento primario
    se muestra en mayúsculas, salvo en palabras de una sola sílaba (no hay
    contraste de acento que marcar ahí)."""
    entries = _cmu.get(word.lower())
    if not entries:
        return None
    syllables = _syllabify_phonemes(entries[0])
    parts = []
    for syl in syllables:
        letters = "".join(_ARPABET_TO_RESPELL.get(re.sub(r"\d$", "", p), "") for p in syl)
        if len(syllables) > 1 and any(p.endswith("1") for p in syl):
            letters = letters.upper()
        parts.append(letters)
    return "-".join(parts)


def expected_focus_phoneme(word: str) -> tuple[str, str] | None:
    """Fonema (ARPAbet, IPA) con acento primario según CMU dict, o None si
    la palabra no está en el diccionario."""
    entries = _cmu.get(word.lower())
    if not entries:
        return None
    phonemes = entries[0]
    for p in phonemes:
        if p.endswith("1"):
            ipa = arpabet_to_ipa(p)
            return (p, ipa) if ipa else None
    return None


_model = None
_processor = None


def _get_model():
    global _model, _processor
    if _model is None:
        from transformers import Wav2Vec2ForCTC, Wav2Vec2Processor

        _processor = Wav2Vec2Processor.from_pretrained("facebook/wav2vec2-lv-60-espeak-cv-ft")
        _model = Wav2Vec2ForCTC.from_pretrained("facebook/wav2vec2-lv-60-espeak-cv-ft")
    return _model, _processor


def recognize_phonemes(waveform: np.ndarray, sr: int, start: float, end: float) -> list[str]:
    """Reconoce los fonemas (IPA) realmente producidos en [start, end] del
    audio, con un modelo de reconocimiento fonético (wav2vec2 + CTC) —
    independiente del texto esperado, a diferencia de un ASR normal como
    Whisper (que tiende a "autocorregir" a la palabra correcta)."""
    import torch

    if sr != 16000:
        import librosa

        waveform = librosa.resample(waveform, orig_sr=sr, target_sr=16000)
        sr = 16000
    segment = waveform[int(start * sr) : int(end * sr)]
    if segment.size == 0:
        return []
    model, processor = _get_model()
    inputs = processor(segment, sampling_rate=sr, return_tensors="pt")
    with torch.no_grad():
        logits = model(inputs.input_values).logits
    pred_ids = torch.argmax(logits, dim=-1)
    transcription = processor.batch_decode(pred_ids)[0]
    return transcription.split()


def count_words_evaluated(words: list[dict], target_words: list[str]) -> int:
    """Cuenta cuántas target_words aparecen en la transcripción y son
    evaluables por analyze_phonemes (están en CMU dict) — a diferencia de
    analyze_stress, no importa el número de sílabas. Usado para poder
    calcular un accuracy real (correct = evaluated - len(phoneme_errors))
    incluso para patrones cuya familia es 100% monosílaba, donde
    analyze_stress nunca genera stress_results (bug real: esos patrones se
    quedaban con accuracy congelada en 0.0 para siempre y dominaban la
    selección de "menos practicado")."""
    target_lower = {w.lower() for w in target_words}
    count = 0
    for w in words:
        word_text = w["w"].strip(".,!?").lower()
        if word_text not in target_lower:
            continue
        if expected_focus_phoneme(word_text) is None:
            continue
        count += 1
    return count


def analyze_phonemes(
    waveform: np.ndarray, sr: int, words: list[dict], target_words: list[str]
) -> list[dict]:
    """Para cada palabra objetivo presente en la transcripción, compara el
    fonema con acento primario esperado (CMU dict) contra si aparece en los
    fonemas realmente producidos (wav2vec2). Solo devuelve las incorrectas
    (son "errores", igual que el resto de la respuesta de /transcribe)."""
    target_lower = {w.lower() for w in target_words}
    errors = []
    for w in words:
        word_text = w["w"].strip(".,!?").lower()
        if word_text not in target_lower:
            continue
        expected = expected_focus_phoneme(word_text)
        if expected is None:
            continue
        expected_arpabet, expected_ipa = expected
        produced = recognize_phonemes(waveform, sr, w["start"], w["end"])
        if expected_ipa not in produced:
            errors.append(
                {
                    "word": word_text,
                    "expected": expected_arpabet,
                    "produced": " ".join(produced),
                }
            )
    return errors
