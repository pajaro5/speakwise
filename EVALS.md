# EVALS — Cómo saber que algo funciona antes de construirlo

Cada eval tiene un criterio de pass/fail explícito. Un eval "pasa" cuando todos sus checks son ✅.

---

## EVAL-02 — Curriculum Engine (cierre de ITER-1)

Verifica que `GET /api/today` (`services/curriculum.py`) hace lo que promete `DESIGN.md` §7.

```
□ Con datos de seed conocidos, "Formas a revisar" devuelve las formas con
  next_review <= hoy y context = conv_prod, ordenadas por score ASC, máx. 5
□ "Patrón del día" devuelve 1 patrón con stage < 4, el de menor accuracy
□ "Chunk del día" pertenece al top-150 palabras con menor chunk_spontaneous acumulado
□ "Dificultad" es "increase" si AVG(comprehensibility) últimas 5 sesiones > 4.0,
  "decrease" si < 3.0, si no "maintain"
□ El JSON de respuesta cumple exactamente el contrato de DESIGN.md §5
□ El contenido total del corpus en la respuesta es ≤ 300 tokens
□ Responde en < 500ms (medido con datos reales de seed, no mocks)
```

**Pass:** los 7 checks en verde. Automatizado en `tests/services/test_curriculum.py` + `tests/routers/test_progress.py`.

---

## EVAL-06 — End-to-End sin fricciones (cierre de ITER-1)

Verifica una sesión completa de 20 minutos de principio a fin. Manual — se corre desde el móvil y desde PC, no es automatizable con el stack actual.

```
□ Abrir la app desde el móvil (PWA o browser) sin errores de carga
□ Grabar audio de un turno de conversación → transcripción aparece en < 10s
□ El tutor (Claude) responde de forma coherente al turno anterior
□ El audio de respuesta (TTS) se reproduce sin cortes
□ Se completan los 3 módulos: nuclear stress + chunk del día + conversación libre
□ La sesión completa dura ~20 minutos sin que la app se caiga o quede colgada
□ Al cerrar, la sesión queda persistida en SQLite (verificable con SELECT * FROM sessions)
□ Repetir el checklist completo sin fricción técnica en 5 días distintos
```

**Pass:** los 8 checks en verde, incluyendo los 5 días. Este es el criterio de "Hecho" de toda la iteración, no solo de un test.

---

## EVAL-01, EVAL-03, EVAL-04, EVAL-05 — pendientes

Corresponden a ITER-2 (análisis fonético), ITER-3 (hoja de trabajo) e ITER-4 (panel de apoyo). Se definen con el mismo formato cuando esas iteraciones entren en progreso — no bloquean ITER-1.

---

## Historial

| Versión | Fecha | Cambio |
|---|---|---|
| 1.0 | Ago 2026 | EVAL-02 y EVAL-06 definidos para cierre de ITER-1; el resto queda pendiente |
