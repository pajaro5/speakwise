# DEFINITION OF DONE · SpeakWise

---

## DoD Global — aplica a todo

- [ ] Corre sin errores en PC Windows y accesible desde móvil vía WiFi
- [ ] No hay regresiones — lo que funcionaba antes sigue funcionando
- [ ] `.env.example` actualizado si se añadieron variables
- [ ] `DESIGN.md` actualizado si cambió schema, API o estructura de archivos
- [ ] Lo usé en al menos 1 sesión real antes de declararlo hecho

---

## DoD por feature

| Feature | Criterios |
|---|---|
| `seed.py` | Idempotente. `word_forms` ≥ 150 registros con `phonemes` ARPAbet y `lfc_focus`. `phonetic_patterns` = 5. ≥ 150 chunks con `function` y `level`. |
| `acoustic.py` (MVP) | WPM y fillers calculados desde Whisper timestamps. Funciona con audio webm del móvil. |
| `acoustic.py` (V2) | `stress_results` con `correct: bool` por frase. `phoneme_errors` con `{word, expected, produced}`. EVAL-01 ≥ 85%. |
| `curriculum.py` | Responde en < 500ms. Contexto ≤ 300 tokens. EVAL-02 pasa. |
| Sesión completa | Ciclo audio → /transcribe → /tutor → /speak en < 10s. Sesión persiste en SQLite. |
| `worksheet.py` | Genera en < 8s. 5 ejercicios específicos a la sesión. Imprimible en A4. EVAL-04 pasa. |
| Panel de apoyo | `prompt_ratio` actualizado tras cada turno. `panel_mode` cambia automáticamente. EVAL-05 pasa. |
| Dashboard | Datos reales de ≥ 30 sesiones. Muestra las 6 métricas del PRD. |

---

## DoD de iteración

Una iteración está hecha cuando:
1. Todos sus tasks pasan su DoD individual
2. Las evals de cierre de la iteración pasan
3. Usé la app diariamente 5 días sin fricción técnica
4. No hay bug bloqueante abierto

---

## Revisión semanal — viernes, 30 minutos

```
□ ¿Cuántas sesiones hice esta semana?
□ ¿El WPM mejoró respecto a la semana anterior?
□ ¿Algo del sistema se sintió roto o confuso?
□ ¿Qué task muevo a "En progreso" la próxima semana?
□ ¿Algún documento necesita actualizarse?
```
