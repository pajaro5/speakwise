# BACKLOG — Product Backlog

**Método:** Kanban. Sin sprints fijos. Una sola cosa en "En progreso" a la vez.  
**Revisión:** 30 minutos los viernes. Qué aprendí usándolo, qué sigue.  
**Criterio de prioridad:** ¿Qué me enseña más rápido si la hipótesis es verdadera?

---

## Tablero actual

```
BACKLOG              │ EN PROGRESO │ EN USO (probando) │ HECHO
─────────────────────┼─────────────┼───────────────────┼───────
ITER-2: Acústico     │ ITER-1      │                   │
ITER-3: Worksheet    │             │                   │
ITER-4: Panel apoyo  │             │                   │
ITER-5: Auto-ajuste  │             │                   │
```

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

- [x] **acoustic.py** — Pipeline básico: Whisper API + WPM + fillers
  - DoD: WPM y fillers calculados correctamente desde timestamps de Whisper

- [x] **curriculum.py** — GET /api/today con las 3 queries básicas
  - DoD: EVAL-02 pasa

- [x] **session.py** — POST /transcribe + /tutor + /speak
  - DoD: ciclo completo audio → texto → Claude → TTS en < 10 seg

- [ ] **Frontend básico** — index.html + app.js + grabación de audio
  - DoD: funciona en Chrome desktop y Chrome móvil

- [ ] **PWA básica** — manifest.json + service-worker.js
  - DoD: instalable en iPhone y Android desde Chrome

- [ ] **Sesión completa** — 3 módulos: nuclear stress + chunk + conversación libre
  - DoD: sesión de 20 min de principio a fin sin errores

- [ ] **EVAL-06** — Correr checklist completo
  - DoD: todos los checks en verde

**Criterio de "En uso":** Usar la app diariamente durante 5 días seguidos.  
**Criterio de "Hecho":** EVAL-06 pasa + 5 días de uso sin fricción técnica.

---

## ITERACIÓN 2 — Análisis fonético completo

**Hipótesis:** ¿El sistema detecta con precisión mis errores fonéticos y me ayuda a corregirlos?  
**Duración estimada:** 1-2 semanas  
**Evals de cierre:** EVAL-01, EVAL-03

### Tasks

- [ ] **acoustic.py** — Integrar Parselmouth para pitch + energy por palabra
  - DoD: `stress_results` en respuesta de /transcribe con `correct: bool` por frase

- [ ] **acoustic.py** — Comparación fonémica WhisperX vs. CMU Dict
  - DoD: `phoneme_errors` incluye `{word, expected, produced}` por turno

- [ ] **patterns.py** — Detección de patrones fonéticos en errores
  - DoD: si produzco 3+ errores de -age/-idge, `pattern_errors` lo reporta

- [ ] **phoneme_log** — Poblar tabla con cada error por sesión
  - DoD: después de una sesión, `SELECT * FROM phoneme_log WHERE session_id = ?` muestra errores reales

- [ ] **Feedback de Claude** — Actualizar system prompt para usar `phoneme_errors` y `stress_results`
  - DoD: EVAL-03 pasa con promedio ≥ 4.0

- [ ] **EVAL-01** — Correr con 20 grabaciones de prueba
- [ ] **EVAL-03** — Correr con 10 transcripciones de prueba

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
