# PLAN VERSIÓN 2 — SpeakWise

**Objetivo de este documento:** plan de ejecución para ITERACIÓN 2 del `BACKLOG.md` ("Análisis fonético completo"), con el mismo rigor de `planVersion1.md`: TDD real, todo verificado contra servicios reales (no solo tests unitarios), y documentado a medida que se construye — no antes.

Fuente: `BACKLOG.md` (ITER-2), `DESIGN.md` §5-6, `PRD.md` (métrica de nuclear stress, línea 77).

---

## 0. Contexto de arranque

El usuario completó ITER-1 (sesión de 3 módulos funcionando, con múltiples rondas de bugs reales encontrados y corregidos probando en vivo — ver `planVersion1.md` Fases 9.1-9.9). Al preguntarle qué seguía, se le explicó el tablero y se activó ITER-2 vía `/goal Iter-2`.

**Hipótesis de ITER-2** (de `BACKLOG.md`): ¿el sistema detecta con precisión mis errores fonéticos y me ayuda a corregirlos?

## 1. Qué pedía el DoD original vs. qué es viable con las herramientas ya instaladas

`DESIGN.md`'s pipeline V2 original (aspiracional, nunca implementado) pedía:

```
Audio → WhisperX → { text, word_timestamps, phoneme_timestamps }
      → CMU Dict  → fonemas esperados por palabra
      → diff      → phoneme_errors[]
      → librosa + Parselmouth → energy/pitch por palabra
      → comparar con CMU stress marker → stress_results[]
      → agrupar errores por patrón → pattern_errors{}
```

**Problema real:** "WhisperX" con alineación fonémica de verdad (timestamps por fonema, típicamente vía wav2vec2 forced alignment) es una dependencia pesada nueva, no instalada, y no evaluada en el hardware del usuario — mismo tipo de restricción que ya descartó Ollama+Qwen 7B en Fase 3 de `planVersion1.md` ("mi PC no es suficiente para correr"). El provider que hoy se llama `WhisperXLocalProvider` en el código es en realidad `faster-whisper` (solo timestamps por palabra, no por fonema) — el nombre es heredado de una decisión anterior, no una alineación fonémica real.

**Decisión:** en vez de bloquear todo ITER-2 en instalar y validar una dependencia pesada de alineación fonémica, construir lo que SÍ es viable con lo ya instalado (`praat-parselmouth`, `librosa`, `cmudict`, `faster-whisper` — todos ya en `pyproject.toml` desde Fase 2/3 de `planVersion1.md`):

- **Sí viable sin forced alignment:** sílaba tónica (stress) — comparar dónde cae el pico de energía/pitch del audio (con solo los timestamps de PALABRA que ya tenemos) contra dónde debería caer según CMU dict. Esto es literalmente la métrica flagship del PRD ("Nuclear stress accuracy ~40% → >75%, medido con Parselmouth + librosa", `PRD.md` línea 77).
- **No viable sin un reconocedor de fonemas dedicado:** `phoneme_errors` (qué fonema produjo el alumno vs. el esperado) — Whisper solo da texto, y normalmente "autocorrige" pronunciaciones imperfectas a la palabra correcta al transcribir, así que no hay señal de qué fonema salió mal. Necesitaría un modelo separado (wav2vec2 vía CTC a fonemas), no evaluado.

Se prioriza stress detection (viable, es la métrica principal del producto) y se documenta honestamente que `phoneme_errors`/`pattern_errors` quedan pendientes de una decisión de scope futura.

---

## 2. Fase 1 — Stress detection (`services/stress.py`) ✅

**TDD, `tests/services/test_stress.py` (11 tests):**
- `expected_stress_syllable(word)` / `syllable_count(word)`: vía `cmudict`, reusa la misma lógica que `seed.py`'s `_lfc_focus_and_stress` pero para cualquier palabra del diccionario, no solo el corpus de 50 lemmas.
- `detect_stress_syllable(waveform, sr, start, end, syllables)`: divide el span de audio en `syllables` partes iguales, usa Parselmouth para medir intensidad por parte, devuelve el índice de mayor pico. Testeado con audio sintético (onda con una mitad fuerte/floja controlada), no depende de grabaciones reales para el test unitario.
- `load_waveform(audio: bytes)`: decodifica audio real (webm/opus del navegador) vía `librosa.load` (que cae a `audioread`/ffmpeg para formatos que `soundfile` no soporta). Testeado con un webm real generado con ffmpeg en el test, no solo WAV.
- `analyze_stress(waveform, sr, words, target_words)`: junta todo — para cada palabra objetivo presente en la transcripción, con ≥2 sílabas y en CMU dict, calcula `{word, expected_syl, detected_syl, correct}`.

**Hallazgo real probando contra audio real (no en los tests unitarios, que usan audio sintético):** la primera versión de `detect_stress_syllable` usaba el **promedio** de intensidad por sílaba. Probado contra audio TTS real (Kokoro diciendo "average", "manage", "nation", "about", "banana"), mostró sesgo sistemático: para palabras con acento en la 1ra sílaba, el promedio favorecía sílabas posteriores casi siempre (probablemente porque el ataque de la consonante inicial diluye el promedio de esa sílaba). Cambiado a **pico** de intensidad por sílaba — mejora consistente en las mismas pruebas ("manage" pasó de detectar sílaba 1 a la 0, correcta). **La precisión real contra voz humana (no TTS) sigue sin validar — eso es EVAL-01, que necesita al usuario.**

Suite tras esta fase: 166/166 (2 de integración deseleccionados).

## 3. Fase 2 — Wiring a /api/transcribe ✅

- `providers/base.py`: `Transcript` gana `stress_results: list[dict]`.
- `services/acoustic.py`: `transcribe_and_analyze()` gana `target_words: list[str] | None` — si se pasa, decodifica el audio (una sola vez, reusando los bytes ya recibidos) y llama `analyze_stress`. Sin `target_words`, no toca el audio para esto (no gasta cómputo en conversación libre, que no lo necesita).
- `routers/session.py`: `POST /api/transcribe` gana el form field opcional `target_words` (string separado por comas) y devuelve `stress_results` en la respuesta.

**Verificado en vivo contra el pipeline real completo** (no solo tests con provider fake): `POST /api/speak` genera audio real con Kokoro diciendo una palabra, ese audio se manda a `POST /api/transcribe` con `target_words` como si fuera la grabación del alumno — confirma que faster-whisper + librosa + Parselmouth decodifican y analizan audio real de punta a punta, no solo datos sintéticos de test.

Suite: 166/166.

## 4. Fase 3 — Accuracy real en pattern_progress + phoneme_log ✅

- `database.py`: `upsert_pattern_progress()` gana `correct`/`total` opcionales — cuando se pasan, `accuracy` se actualiza como promedio acumulado de la proporción correct/total de cada intento (antes quedaba en 0.0 para siempre, un valor muerto desde que se implementó en Fase 9.3 de `planVersion1.md`). Esto activa de verdad la rotación de patrones por accuracy que `_pattern_of_the_day()` ya ordenaba pero nunca tenía datos reales para usar.
- `database.py`: `log_stress_results()` (nuevo) — puebla `phoneme_log` con los intentos **incorrectos** (no todos; el DoD de `BACKLOG.md` pide "errores reales", los correctos no son errores). `phoneme_exp`/`phoneme_got` describen la sílaba esperada vs. detectada (no una sustitución fonémica real — eso requeriría el reconocedor de fonemas que no existe).
- `services/log.py`: `log_pattern_practiced()` gana `session_id`/`stress_results` opcionales, conecta ambos.
- `routers/session.py`: `LogRequest` gana `stress_results` opcional.

Suite: 166/166.

## 5. Fase 4 — Frontend: módulo 1 usa stress_results real ✅

- `app.js`: `transcribeAudio(audioBlob, targetWords)` manda `target_words` cuando se le pasan.
- `handlePatternRecording()`: manda las palabras de la familia del patrón (limpias de markup vía `stripMarkup`, ya existente de Fase 9.7) como `target_words`, manda `stress_results` a `/api/log`, y muestra feedback real ("Stress correct on N/M word(s) — keep practicing!") en vez del "Practiced!" genérico de siempre.

**Verificado en vivo (Chrome, con audio TTS real como sustituto de grabación real):** flujo completo `startSession()` → generar audio real de una palabra de la familia → `handlePatternRecording(audioBlob)` → confirmado `"Stress correct on 1/1 word(s)"` y `pattern_progress.accuracy` actualizado en la DB real (de 0.0 a 0.5 tras un intento correcto y uno incorrecto).

Suite completa: 166/166 (2 de integración deseleccionados).

---

## 6. Qué NO se construyó en esta ronda (documentado en `BACKLOG.md`, no se marca hecho)

- **`phoneme_errors`** — requiere reconocedor de fonemas real, dependencia no evaluada.
- **`pattern_errors`** explícito en la respuesta — el dato equivalente ya vive en `pattern_progress.accuracy` por patrón (real, actualizado), pero no hay una agregación "en esta sesión, X errores de este patrón" si hiciera falta mostrarla puntualmente en algún lado.
- **Integración con el tutor** (system prompt de `services/tutor.py` usando `stress_results`) — `stress_results` hoy solo se usa en el feedback de UI de módulo 1, no en la conversación con el LLM. Módulo 3 (conversación libre) no manda `target_words` a `/api/transcribe` — habría que decidir qué palabras chequear ahí.
- **EVAL-01** (20 grabaciones reales) y **EVAL-03** (10 transcripciones) — pendientes de la voz real del usuario, mismo patrón que EVAL-06 en ITER-1. EVAL-01 en particular es la validación real de si el proxy de pico-de-intensidad sirve en la práctica o necesita más ajuste.

## 7. Comandos de referencia

```powershell
# Verificar stress detection contra audio real (sin usar el micrófono):
# 1. Generar audio real con el TTS:
curl -s -X POST http://localhost:8000/api/speak -H "Content-Type: application/json" -d '{"text": "average"}' -o word.mp3
# 2. Mandarlo como si fuera la grabación del alumno:
curl -s -X POST http://localhost:8000/api/transcribe -F "audio=@word.mp3" -F "target_words=average"

docker compose exec speakwise python -m pytest tests/services/test_stress.py -v
```

---

## Historial

| Versión | Fecha | Cambio |
|---|---|---|
| 1.0 | Ago 2026 | Plan inicial y ejecución de ITER-2 Fase 1-4: stress detection real, conectado a módulo 1, verificado en vivo contra audio real (TTS como sustituto de grabación humana). `phoneme_errors`/`pattern_errors`/integración con tutor/EVAL-01/EVAL-03 documentados como pendientes, no construidos. |
