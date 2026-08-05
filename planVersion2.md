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

## 6.1 Fase 5 — "¿el sistema reconoce lo que digo de verdad?" ✅

El usuario probó módulo 1 diciendo texto sin relación con las palabras del patrón y vio el mismo "Practiced!" genérico de siempre — preguntó si el reconocimiento de voz era real. Sí lo es (Whisper transcribe correctamente), pero el mensaje no lo probaba: cuando `stress_results` viene vacío (ninguna target word detectada en lo que dijo), el código caía al fallback genérico sin importar qué se dijo.

**Fix:** `handlePatternRecording()` ahora muestra la transcripción real cuando no encuentra ninguna palabra objetivo — `I heard: "..." — try saying one of the words above`. Test: `test_app_js_pattern_recording_shows_what_it_heard_when_no_match`.

**Verificado en vivo:** generé audio real con el TTS diciendo "I like pizza on Fridays" (sin relación al patrón del día) y se lo mandé a `handlePatternRecording` como si fuera la grabación del alumno — la app mostró correctamente `I heard: "I like pizza on Fridays." — try saying one of the words above...`, confirmando que la transcripción real llega hasta la UI.

Suite completa: 167/167 (2 de integración deseleccionados).

## 8. Fase 6 — "cerrá bien ITER-2, terminemos todo al 100% correcto"

El usuario pidió cerrar todo lo pendiente de ITER-2 que fuera técnicamente posible sin su voz real (dejando EVAL-01/EVAL-03 explícitamente para cuando él pueda probar).

### 8.1 `phoneme_errors` — sí era viable ✅

`DESIGN.md` original pedía un reconocedor de fonemas dedicado, descartado en la Fase 1 de este plan por asumir que sería tan pesado como Ollama 7B (rechazado en `planVersion1.md` Fase 3 — "mi PC no es suficiente"). **Se verificó en serio antes de descartarlo de nuevo:** `facebook/wav2vec2-lv-60-espeak-cv-ft` (315M parámetros, mismo orden de magnitud que lo que ya corre bien — faster-whisper, Kokoro) carga en ~56s (una vez, se cachea) y hace inferencia en ~0.5s por palabra sobre CPU. `torch`/`transformers` ya estaban instalados (dependencia de Kokoro). Viable de verdad, no una suposición.

**`services/phoneme.py` (nuevo):**
- `arpabet_to_ipa()`: mapeo ARPAbet → IPA, con caso especial para AH/ER (schwa átono vs. vocal plena acentuada — coincide con lo que el modelo real distingue).
- `expected_focus_phoneme(word)`: fonema (ARPAbet, IPA) con acento primario según CMU dict — mismo scope acotado que el ejemplo de `DESIGN.md` (`{"word": "average", "expected": "AE1", "produced": "AH1"}`, un fonema focal, no la palabra entera).
- `recognize_phonemes()`: reconoce los fonemas IPA realmente producidos en un tramo de audio — independiente del texto esperado, a diferencia de Whisper (que "autocorrige" a la palabra correcta).
- `analyze_phonemes()`: compara, devuelve solo los errores (fonema esperado ausente de lo producido).

Tests rápidos (lógica pura, sin cargar el modelo) + 1 test `@pytest.mark.integration` contra el modelo y audio TTS real (mismo patrón que Kokoro — excluido del run por defecto, no gasta tiempo/ancho de banda en cada corrida de CI).

**Verificado en vivo contra el pipeline real completo:** `POST /api/transcribe` con audio TTS real de "banana" devolvió `phoneme_errors: [{"word": "banana", "expected": "AE1", "produced": "b ə n aː n"}]` — detectó que la vocal tónica esperada (æ) no apareció en lo producido (aː, una vocal cercana pero distinta). Confirmado también que el pipeline preserva UTF-8 correctamente de punta a punta vía navegador (un intento manual de probarlo con `curl` tipeando IPA directamente en la terminal de Windows corrompió los caracteres — eso era el shell, no la app; confirmado re-verificando vía Chrome).

### 8.2 `pattern_errors` ✅

`transcribe_and_analyze()` gana `pattern_name` opcional — si se pasa, agrupa las palabras únicas con error (stress o fonema) bajo ese nombre: `{"schwa": 1}`. Módulo 1 lo manda automáticamente (`todaysPlan.pattern_focus.name`). Verificado en vivo: `pattern_errors: {"schwa": 1}` en la misma respuesta que el `phoneme_errors` de arriba.

### 8.3 `phoneme_log` ahora tiene datos fonémicos reales ✅

`log_phoneme_errors()` (nuevo, `database.py`) guarda los `phoneme_errors` reales en `phoneme_log` — a diferencia de `log_stress_results()` (que solo tenía posiciones de sílaba como placeholder), esto es una comparación fonémica de verdad. Verificado contra la DB real vía el flujo del navegador: `phoneme_exp='AE1'`, `phoneme_got` con el carácter IPA correcto (U+0259, "ə") preservado.

### 8.4 Integración con el tutor (módulo 3) ✅

Último ítem pendiente de la lista original. `services/tutor.py`: `_build_system_prompt()`/`get_tutor_reply()` ganan `stress_results` opcional — si hay palabras con acento incorrecto, se agrega una nota al prompt pidiéndole al tutor que lo mencione "con calidez... sin forzarlo" (mismo tono que ya se usa para `chunk_today`/`week_words`). `POST /api/tutor` gana `stress_results` en el request. Frontend: módulo 3 manda las palabras de la semana (`todaysPlan.week_words`) como `target_words` a `/api/transcribe`, y reenvía el `stress_results` resultante a `/api/tutor`.

**Verificado en vivo contra DeepSeek real:** con `stress_results` marcando "banana" con acento incorrecto, en una conversación donde tenía sentido preguntarlo, el tutor respondió con una corrección específica y útil: *"You say it like this: buh-NA-nuh. The stress is on the second syllable: NA..."* — no lo menciona cada turno (es una nota "si tiene sentido", no una corrección forzada), que es el comportamiento diseñado.

Suite completa: 187/187 (3 de integración deseleccionados — Kokoro, DeepSeek, y ahora el reconocedor de fonemas).

### 8.5 Lo único que sigue pendiente: EVAL-01 y EVAL-03

No se pueden cerrar sin la voz real del usuario — todo lo demás de la lista original de ITER-2 está construido y verificado contra servicios reales (no solo mocks). Ver `BACKLOG.md` para el detalle actualizado.

## 9. Comandos de referencia

```powershell
# Verificar el pipeline completo (stress + phoneme + pattern) contra audio real:
curl -s -X POST http://localhost:8000/api/speak -H "Content-Type: application/json" -d '{"text": "banana"}' -o word.mp3
curl -s -X POST http://localhost:8000/api/transcribe -F "audio=@word.mp3" -F "target_words=banana" -F "pattern_name=schwa"

docker compose exec speakwise python -m pytest tests/services/test_stress.py tests/services/test_phoneme.py -v
docker compose exec speakwise python -m pytest -m integration -v   # incluye el modelo de fonemas real (~1.2GB, primera vez)
```

---

## Historial

| Versión | Fecha | Cambio |
|---|---|---|
| 1.0 | Ago 2026 | Plan inicial y ejecución de ITER-2 Fase 1-4: stress detection real, conectado a módulo 1, verificado en vivo contra audio real (TTS como sustituto de grabación humana). `phoneme_errors`/`pattern_errors`/integración con tutor/EVAL-01/EVAL-03 documentados como pendientes, no construidos. |
