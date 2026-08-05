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
