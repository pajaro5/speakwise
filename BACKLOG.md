# BACKLOG — Product Backlog

**Método:** Kanban. Sin sprints fijos. Una sola cosa en "En progreso" a la vez.  
**Revisión:** 30 minutos los viernes. Qué aprendí usándolo, qué sigue.  
**Criterio de prioridad:** ¿Qué me enseña más rápido si la hipótesis es verdadera?

---

## Tablero actual

```
BACKLOG              │ EN PROGRESO │ EN USO (probando) │ HECHO
─────────────────────┼─────────────┼───────────────────┼───────
ITER-3: Worksheet    │ ITER-2      │ ITER-1             │
ITER-4: Panel apoyo  │             │                   │
ITER-5: Auto-ajuste  │             │                   │
```

ITER-1 pasó a "En uso" — código completo y verificado en vivo módulo por módulo, falta el uso real de varios días seguidos que pide su propio criterio de "Hecho". ITER-2 arrancó: stress detection (Parselmouth) construido y verificado en vivo end-to-end; phoneme_errors/pattern_errors/integración con el tutor/EVAL-01/EVAL-03 quedan pendientes (detalle en la sección de ITER-2).

> La columna "En uso" existe porque yo soy el usuario. Antes de mover algo a "Hecho", lo uso en al menos 3 sesiones reales. Si algo no funciona en la práctica diaria, no está hecho.

---

## ITERACIÓN 1 — Sesión básica funcional

**Hipótesis:** ¿Puedo tener una conversación de 20 minutos con el tutor sin fricciones técnicas?  
**Duración estimada:** 1-2 semanas de desarrollo  
**Evals de cierre:** EVAL-02 (Curriculum Engine) · EVAL-06 (End-to-End sin fricciones)

### Tasks

- [x] **seed.py** — Poblar corpus con top 50 lemmas (GSL) + todas sus formas + fonemas CMU + traducción ES
  - DoD: `SELECT COUNT(*) FROM word_forms` retorna ≥ 150 registros
  - DoD: Cada forma tiene `phonemes` en formato ARPAbet y `lfc_focus`

- [x] **seed.py** — Añadir 5 patrones fonéticos prioritarios con sus familias
  - Patrones: -age/-idge, -tion/-sion, sílabas elididas, letras mudas kn-/wr-, schwa
  - DoD: `SELECT COUNT(*) FROM phonetic_patterns` = 5

- [x] **seed.py** — Añadir chunks por forma verbal (top 50 lemmas × sus tiempos)
  - DoD: ≥ 150 chunks con `function` y `level` definidos
  - Estado: 200 chunks (50 lemmas × 4 tenses). El verbo irregular "be" no encajaba en los templates genéricos (producía frases no gramaticales, p. ej. "I be this every day.") — corregido con `IRREGULAR_CHUNKS` en `seed.py`, chunks curados a mano con contexto de uso.

- [x] **acoustic.py** — Pipeline básico: Whisper API + WPM + fillers
  - DoD: WPM y fillers calculados correctamente desde timestamps de Whisper

- [x] **curriculum.py** — GET /api/today con las 3 queries básicas
  - DoD: EVAL-02 pasa

- [x] **session.py** — POST /transcribe + /tutor + /speak
  - DoD: ciclo completo audio → texto → Claude → TTS en < 10 seg

- [x] **Frontend básico** — index.html + app.js + grabación de audio
  - DoD: funciona en Chrome desktop y Chrome móvil
  - Estado: confirmado por el usuario en Chrome desktop Y Chrome móvil (por WiFi, con el flag de Chrome para permitir micrófono sin HTTPS) — grabación, transcripción, respuesta del tutor (DeepSeek) y audio de respuesta (Kokoro) funcionan de punta a punta en ambos.

- [x] **PWA básica** — manifest.json + service-worker.js
  - DoD: instalable en iPhone y Android desde Chrome
  - Estado: **instalación confirmada en Android** por el usuario — ícono aparece en pantalla de inicio. iPhone queda fuera de alcance de esta verificación: el usuario no tiene el dispositivo (nota: además, PWA en iPhone se instala desde Safari, no Chrome — es una limitación de iOS, no del código).

- [x] **Sesión completa** — 3 módulos: nuclear stress + chunk + conversación libre
  - DoD: sesión de 20 min de principio a fin sin errores
  - Estado: código completo y verificado contra la DB/APIs reales (backend + frontend, 17 tests nuevos). 2 bugs reales encontrados y corregidos probando en vivo (auto-stop de grabación en módulos 1/2; service worker sirviendo HTML viejo — cache-first → network-first). El usuario corrió la sesión completa de punta a punta con micrófono real y reportó 4 problemas concretos, los 4 corregidos con TDD: (1) feedback visual de grabación poco claro → texto/estado de botón dinámico; (2) el tutor mezclaba español → instrucción explícita de inglés-solo en el system prompt; (3) módulo 3 sin apoyo léxico ("me quedo en blanco") → panel de apoyo inicial; (4) chunk de "be" sin contexto/no gramatical → chunks curados a mano. De paso, se encontró y corrigió que `pyproject.toml` no estaba en bind-mount, por lo que el fix de Fase 6 (excluir tests de integración del run por defecto) nunca llegó a la imagen corriendo — cada suite completa gastaba una llamada real a DeepSeek. Tras probar el fix #3, el usuario pidió afinarlo con 3 categorías concretas en vez de una lista plana: frases para iniciar la charla, conectores de ideas (ej. "for example", "between"), y temas — implementado en `curriculum.py` (`CONVERSATION_STARTERS`/`LINKING_WORDS`, pools curados igual que `topic_options`) y expuesto en `/api/today`. No es el panel adaptativo completo de ITER-4 (sin fading logic ni tracking de `prompts_used`), solo apoyo estático para no bloquear la conversación. Después el usuario probó módulo 1 y reportó 3 observaciones más: (a) el botón "Escuchar ejemplos" no se deshabilitaba mientras cargaba el TTS real, así que seguía presionándolo → arreglado, se deshabilita al hacer clic y se reactiva cuando arranca la reproducción (mismo fix aplicado también al botón "Escuchar" de módulo 2, mismo bug); (b) pidió mostrar cómo pronunciar el patrón, no solo la regla en español → se expone `rule_ipa` (ya existía en la DB pero `_pattern_of_the_day()` no lo seleccionaba) en un elemento destacado; (c) preguntó si era correcto que siempre empezara con "-age/-idge" → no del todo: sin scoring real de precisión (eso es ITER-2), el orden nunca cambiaba porque `sessions_practiced` no influía — se agregó como criterio de desempate para rotar entre patrones ya practicados, igual que ya hacía `chunk_of_the_day` con `spontaneous_uses`. Después probó módulo 2 (chunk del día) y pidió 3 ejemplos de uso — oración simple, párrafo, conversación. Curar 200 chunks × 3 ejemplos a mano no escala, así que se generan bajo demanda con el LLM configurado (`services/chunk_examples.py`, `POST /api/chunk-examples`), cargados automáticamente al entrar a módulo 2. Verificado en vivo contra DeepSeek real: ejemplos coherentes y en contexto para "Be careful with that.". Probando esos ejemplos reportó 4 ajustes más: prompt reforzado para prohibir español explícitamente; saltos de línea de la conversación se veían como "\n" literal (backslash doblado del LLM, normalizado + CSS `white-space: pre-line`); íconos (✏️📄💬) en vez de labels en español; y el chunk resaltado en negrita siempre, incluso dentro de los 3 ejemplos generados (con un bug real encontrado en vivo: el LLM a veces sigue la oración después del chunk sin el punto final, así que había que ignorar puntuación final al buscar coincidencias). Después pidió que toda la interfaz esté en inglés (botones, títulos, mensajes) — se confirmó el alcance con el usuario primero (¿también las reglas de pronunciación en español? no, esas quedan igual, es una técnica pedagógica a propósito) y se tradujo `index.html`/`app.js` completo, con test de regresión que verifica ausencia de los textos viejos en español. Después preguntó cómo mejorar "sílabas elididas", donde no quedaba claro qué sílaba no se pronuncia — se acordó curar a mano qué parte resaltar por palabra (25 palabras en 5 patrones) en vez de intentar derivarlo del CMU dict, con markup `~x~`/`*x*` en `family` renderizado como tachado/resaltado en el frontend, y el mismo bug de re-seed-no-actualiza que tuvieron los chunks de "be" (arreglado igual, con `UPDATE`). Después reportó que dijo el chunk correctamente ("Be careful with that") y no lo detectó, dejándolo avanzar igual con un mensaje genérico — bug real: el match exacto comparaba contra el chunk CON punto final vs. el transcript de Whisper SIN punto (mismo problema que el resaltado, ahora en la detección de verdad), arreglado ignorando puntuación final; y cambio de UX: si no detecta, ya no avanza — pide repetir la grabación y oculta el botón "Next" hasta lograrlo. Después pidió que módulo 3 sea tipo chat (look and feel WhatsApp): reemplazados los elementos fijos de transcript/reply/audio por un `#chat-log` scrolleable donde cada grabación agrega burbujas (usuario a la derecha en verde, tutor a la izquierda en blanco) con scroll automático al final. Después reportó texto markdown literal (`**"phoneme"**`) en el chat que además el TTS leía en voz alta ("asterisk phoneme") — arreglado en el origen (system prompt del tutor prohíbe markdown explícitamente, verificado en vivo que DeepSeek se niega a usarlo incluso pidiéndoselo a propósito) más una limpieza defensiva (`stripMarkdown()`) antes de mostrar/hablar la respuesta.

- [x] **EVAL-06** — Correr checklist completo
  - DoD: todos los checks en verde
  - Estado: sesión completa verificada con micrófono real por el usuario; los 4 problemas encontrados en esa verificación ya están corregidos y reverificados (suite 118/118 relevantes, 2 de integración deseleccionados correctamente). Pendiente: que el usuario re-confirme la sesión completa ya con los 4 fixes aplicados.

**Criterio de "En uso":** Usar la app diariamente durante 5 días seguidos.  
**Criterio de "Hecho":** EVAL-06 pasa + 5 días de uso sin fricción técnica.

---

## ITERACIÓN 2 — Análisis fonético completo

**Hipótesis:** ¿El sistema detecta con precisión mis errores fonéticos y me ayuda a corregirlos?  
**Duración estimada:** 1-2 semanas  
**Evals de cierre:** EVAL-01, EVAL-03

### Tasks

- [x] **acoustic.py** — Integrar Parselmouth para pitch + energy por palabra
  - DoD: `stress_results` en respuesta de /transcribe con `correct: bool` por frase
  - Estado: hecho y verificado en vivo contra servicios reales (no solo tests). `services/stress.py` (nuevo): `load_waveform()` decodifica el audio real del navegador (webm/opus) vía librosa/ffmpeg; `detect_stress_syllable()` divide la palabra en N sílabas (según CMU dict) y usa el **pico** de intensidad por sílaba (Parselmouth) como proxy de sílaba tónica — no hay alineación fonémica real, es una heurística de mínimo esfuerzo. `POST /api/transcribe` acepta `target_words` opcional (form field) y devuelve `stress_results`. Conectado a módulo 1: manda las palabras de la familia del patrón, muestra "Stress correct on N/M words" en vez de "Practiced!" genérico, y `pattern_progress.accuracy` ahora se actualiza de verdad (antes quedaba en 0.0 para siempre — esto además activa la rotación de patrones por `sessions_practiced`/`accuracy` ya implementada en Fase 9.3). **Hallazgo real probando en vivo**: la primera versión (promedio de intensidad por sílaba) tenía sesgo sistemático hacia sílabas posteriores — cambiado a **pico** de intensidad, mejora consistente en las pruebas contra TTS real pero **la precisión real contra voz humana no está validada, eso es EVAL-01**.
  - `phoneme_log` poblado con los intentos incorrectos (no todos, solo "errores reales" per el DoD de esa task) vía `log_stress_results()`.

- [ ] **acoustic.py** — Comparación fonémica WhisperX vs. CMU Dict
  - DoD: `phoneme_errors` incluye `{word, expected, produced}` por turno
  - Estado: no construido. Requiere un reconocedor de fonemas real (el STT actual solo da texto, no fonemas producidos) — Whisper suele "autocorregir" pronunciaciones imperfectas al transcribir la palabra correcta, así que comparar el texto transcripto contra el esperado no detecta desviaciones fonéticas sutiles. Necesitaría un modelo de reconocimiento fonético dedicado (ej. wav2vec2 vía CTC a fonemas), dependencia pesada nueva — no evaluado si corre bien en el hardware del usuario (mismo tipo de restricción que descartó Ollama 7B). Pendiente de decisión.

- [ ] **patterns.py** — Detección de patrones fonéticos en errores
  - DoD: si produzco 3+ errores de -age/-idge, `pattern_errors` lo reporta
  - Estado: no construido como `pattern_errors` explícito en la respuesta — pero el dato equivalente ya vive en `pattern_progress.accuracy`/`sessions_practiced` por patrón, que sí es real y se actualiza. Falta la agregación puntual "en esta sesión, X errores de este patrón" si hace falta mostrarla en algún lado.

- [x] **phoneme_log** — Poblar tabla con cada error por sesión
  - DoD: después de una sesión, `SELECT * FROM phoneme_log WHERE session_id = ?` muestra errores reales
  - Estado: hecho — ver arriba (`log_stress_results()`), verificado con test dedicado.

- [ ] **Feedback de Claude** — Actualizar system prompt para usar `phoneme_errors` y `stress_results`
  - DoD: EVAL-03 pasa con promedio ≥ 4.0
  - Estado: no construido. `stress_results` hoy solo se usa en módulo 1 (feedback de UI simple, no vía el tutor/LLM). Integrarlo al tutor tendría sentido para módulo 3, pero conversación libre no manda `target_words` a `/api/transcribe` todavía — necesitaría decidir qué palabras chequear ahí (¿las de la semana? ¿cualquiera del corpus?).

- [ ] **EVAL-01** — Correr con 20 grabaciones de prueba
  - Estado: pendiente — necesita la voz real del usuario, no se puede correr sin él (mismo patrón que EVAL-06). Es la validación real de si el proxy de pico-de-intensidad sirve o hace falta ajustarlo más.
- [ ] **EVAL-03** — Correr con 10 transcripciones de prueba
  - Estado: pendiente — depende del feedback del tutor con `stress_results`/`phoneme_errors`, que todavía no está integrado.

**Criterio de "Hecho":** EVAL-01 + EVAL-03 pasan + 1 semana de uso donde el feedback fonético se siente preciso.

---

## ITERACIÓN 3 — Hoja de trabajo

**Hipótesis:** ¿La hoja de trabajo generada al final de cada sesión me ayuda a reforzar lo aprendido a través de la escritura?  
**Duración estimada:** 1 semana  
**Eval de cierre:** EVAL-04

### Tasks

- [ ] **worksheet.py** — Servicio de generación: lee datos de sesión + llama Claude para ejercicios
  - DoD: Claude devuelve JSON con 5 ejercicios válidos para la sesión

- [ ] **templates/worksheet.html** — Template Jinja2 con @media print CSS
  - DoD: imprimible en A4, cabe en una hoja, legible a mano

- [ ] **session.py** — POST /api/worksheet/{session_id}
  - DoD: retorna HTML válido, descargable desde el móvil

- [ ] **Frontend** — Botón "Descargar hoja de trabajo" en la pantalla de cierre de sesión
  - DoD: abre la hoja en una nueva tab del browser

- [ ] **Verificación de correctitud** — Los ejercicios tienen las respuestas correctas fonéticamente
  - DoD: el ejercicio "marcar el stress" tiene la sílaba tónica correcta

- [ ] **EVAL-04** — Completar 5 hojas de trabajo a mano durante 5 días

**Criterio de "Hecho":** EVAL-04 pasa + las hojas se sienten útiles, no relleno.

---

## ITERACIÓN 4 — Panel de apoyo contextual

**Hipótesis:** ¿El panel de vocabulario reduce los momentos de mente en blanco y mejora el WPM en las primeras semanas?  
**Duración estimada:** 1 semana  
**Eval de cierre:** EVAL-05

### Tasks

- [ ] **curriculum.py** — `build_support_panel()`: vocabulario + chunks + fillers
  - DoD: el panel contiene exactamente las palabras de la semana actual con traducción ES

- [ ] **progress.py** — GET /api/panel
  - DoD: responde en < 200ms (todo viene de SQLite)

- [ ] **Frontend** — Panel lateral en pantalla de conversación libre
  - DoD: visible en PC y móvil, no tapa el área de chat

- [ ] **Tracking** — Detectar palabras del panel en transcripción → actualizar `prompts_used`
  - DoD: `prompt_ratio` en sessions se actualiza correctamente tras cada turno

- [ ] **Fading logic** — Cambio automático de `panel_mode` según `prompt_ratio`
  - DoD: después de 5 sesiones con ratio < 0.5, el modo cambia a `tap_to_show`

- [ ] **Dashboard** — Barra de autonomía léxica en progreso
  - DoD: muestra `1 - AVG(prompt_ratio)` de las últimas 30 sesiones

- [ ] **EVAL-05** — 5 sesiones con panel + 5 sesiones sin panel, comparar WPM

**Criterio de "Hecho":** EVAL-05 pasa + el panel se siente como red de seguridad, no como distracción.

---

## ITERACIÓN 5 — Sistema de progreso y auto-ajuste

**Hipótesis:** ¿Después de 2 semanas de uso, el sistema elige qué practicar sin que yo configure nada manualmente?  
**Duración estimada:** 1-2 semanas  
**Eval de cierre:** revisión manual del historial de sesiones

### Tasks

- [ ] **spaced_rep.py** — SM-2 completo para formas verbales y patrones fonéticos
  - DoD: `next_review` se actualiza correctamente según score y consecutive_hits

- [ ] **Curriculum Engine completo** — Auto-ajuste de dificultad y énfasis
  - DoD: si `stress_correct < 0.60`, el engine prioriza módulo de stress automáticamente

- [ ] **Dashboard completo** — WPM trend, fonemas por accuracy, patrones por stage, chunks
  - DoD: el dashboard muestra las 6 métricas del PRD con datos reales de 2 semanas

- [ ] **Corpus completo** — Expandir a top 200 lemmas
  - DoD: `SELECT COUNT(DISTINCT word_id) FROM word_forms` ≥ 200

- [ ] **Revisión de 2 semanas** — ¿El sistema elige bien qué practicar?
  - DoD subjetivo: el tutor se siente personalizado, no genérico

---

## Backlog futuro (no priorizado)

Estos items existen pero no tienen fecha. Se priorizan cuando alguna iteración los desbloquea o cuando el uso diario los hace necesarios.

- [ ] Corpus completo (top 1,000 lemmas)
- [ ] Modelos locales: WhisperX self-hosted + Kokoro + Ollama
- [ ] Análisis de entonación completa (más allá de nuclear stress)
- [ ] Modo offline en móvil (whisper.cpp + Kokoro ONNX)
- [ ] Exportar historial completo de progreso a CSV
- [ ] Modo de revisión: repasar hojas de trabajo anteriores
- [ ] Detección automática de fossilización (el mismo error en > 10 sesiones)

---

## Cómo actualizar este backlog

Cada viernes:
1. ¿Qué terminé esta semana? → mover a "Hecho"
2. ¿Qué aprendí usándolo? → ¿cambia alguna prioridad?
3. ¿Qué sigue? → mover 1 item a "En progreso"
4. ¿Apareció algún bug o fricción? → añadir como task en la iteración actual

No añadir items al backlog durante la semana — apuntarlos en notas y revisarlos el viernes.
