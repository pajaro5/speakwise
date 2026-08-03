# PRD — Product Requirements Document

**Producto:** SpeakWise  
**Versión:** 1.0  
**Fecha:** Julio 2025  
**Estado:** Activo  

---

## 1. El Problema

Tengo conocimiento pasivo del inglés (vocabulario, gramática, comprensión lectora) pero no puedo sostener una conversación fluida. Tres brechas específicas:

1. **Mente en blanco** — En situaciones de habla real, el acceso léxico colapsa bajo cognitive overload. Sé las palabras pero no puedo recuperarlas en tiempo real.
2. **Pronunciación que interfiere** — Ciertos rasgos fonéticos (nuclear stress incorrecto, patrones ortografía-pronunciación desconocidos) reducen mi inteligibilidad aunque el mensaje sea correcto.
3. **Sin práctica diaria estructurada** — Las apps existentes (Duolingo, ELSA Speak) o son demasiado gamificadas o solo trabajan pronunciación sin conversación real.

### Lo que no es el problema

No necesito sonar como un hablante nativo americano. Necesito ser comprendido por cualquier persona — colombiana, alemana, japonesa, americana — cuando hablo en inglés.

---

## 2. Filosofía Pedagógica

### Inteligibilidad sobre natividad

**Fundamento académico:** Munro & Derwing (1995-2020) demostraron que acento e inteligibilidad son dimensiones independientes. El habla puede tener acento fuerte y ser altamente inteligible. El consenso actual en investigación de pronunciación L2 es que la meta debe ser inteligibilidad, no natividad.

**Implicación práctica:** El sistema mide si el mensaje fue comprendido, no si la pronunciación se parece a un nativo americano. El acento propio es identidad, no defecto.

### Los cuatro hilos de Nation (1990-2001)

Cada sesión combina cuatro tipos de actividad sobre el **mismo vocabulario**:

| Hilo | Actividad | Tiempo |
|---|---|---|
| ① Input comprensible | Escuchar — Claude narra con el vocabulario de la semana | 3-4 min |
| ② Output significativo | Hablar — conversación libre con objetivo comunicativo real | 8-10 min |
| ③ Aprendizaje focalizado | Trabajar — patrones fonéticos, nuclear stress, chunks | 5-6 min |
| ④ Fluidez | Automatizar — shadowing sin corrección | 3-4 min |

### El LFC como guía de prioridades

Jenkins' Lingua Franca Core (2000) orienta qué rasgos fonéticos trabajar primero. El LFC es un **marco de priorización**, no una lista definitiva:

1. **Nuclear stress** — el de mayor impacto en inteligibilidad
2. **Consonant clusters** — críticos en ELF
3. **Longitud vocálica** — ship/sheep (duración, no calidad exacta)
4. **Consonantes esenciales** — todas excepto /θ/ y /ð/ como baja prioridad

> **⚠ Nota académica:** La exclusión de /θ/ /ð/ en Jenkins (2000) tiene evidencia parcial. El LFC se usa como guía de prioridades, no como dogma. Se enseñan, pero con menor urgencia que el nuclear stress.

---

## 3. El Usuario

**Hay un solo usuario: yo.**

- Hispanohablante nativo (español como L1)
- Conocimiento pasivo de inglés: nivel B1-B2
- Objetivo: hablar inglés con fluidez en contextos laborales y sociales
- Disponibilidad: 20-30 minutos diarios
- Dispositivos: PC (Windows) + iPhone/Android en la misma red WiFi

No hay otros usuarios. No hay métricas de retención de terceros. No hay monetización. Esto simplifica radicalmente el diseño.

---

## 4. Métricas de Éxito

El proyecto funciona si, después de 8 semanas de uso diario:

| Métrica | Línea base | Meta semana 8 | Fuente |
|---|---|---|---|
| WPM en conversación libre | ~72 | > 100 | Whisper timestamps |
| Nuclear stress accuracy | ~40% | > 75% | Parselmouth + librosa |
| Comprensibilidad (1-5) | ~2.8 | > 4.0 | Claude evalúa consistentemente |
| Chunks usados espontáneamente | 0% | > 60% | Text match en transcripción |
| Autonomía léxica (sin panel) | 0% | > 75% | prompt_ratio en sessions |
| Formas verbales en vocab. productivo | 0 | > 50 | conv_prod exposures ≥ 3 |

**La métrica más importante:** ¿Uso la app voluntariamente cada día? Si no hay adherencia, el resto no importa.

---

## 5. Las 1,000 Palabras como Base de Contenido

Las 1,000 palabras más frecuentes del inglés hablado (GSL / SUBTLEX-US) cubren el 85% del vocabulario en conversación diaria. Son la columna vertebral del contenido.

**Principio crítico:** las 1,000 palabras son **familias de formas**, no entradas únicas. Cada lemma tiene múltiples formas con perfiles fonémicos distintos:

```
"think" → think / thinking / thought
           /θɪŋk/  /θɪŋkɪŋ/   /θɔːt/  ← perfiles completamente distintos
```

Las 1,000 palabras representan ~2,500-3,000 unidades fonológicas activas. El sistema rastrea exposiciones **por forma**, no por lemma.

---

## 6. Alcance

### En alcance — MVP

- Sesión de conversación guiada (20 min) con tutor Claude
- Elección de tema al inicio (3 opciones random + libre)
- Módulo de nuclear stress (awareness + producción)
- Chunk del día (presentación + uso forzado + tracking)
- Panel de apoyo contextual (vocabulario + chunks + fillers)
- Análisis acústico: WPM, nuclear stress, phoneme comparison
- Hoja de trabajo generada al final de cada sesión (HTML imprimible)
- Dashboard básico de progreso
- Acceso desde móvil vía PWA en red local

### Fuera de alcance — MVP

| Feature | Por qué espera |
|---|---|
| Múltiples usuarios / auth | Solo soy yo |
| App móvil nativa (React Native) | PWA es suficiente para validar |
| Modelos LLM locales (Ollama) | Costo marginal de APIs es irrelevante a esta escala |
| Análisis de entonación completa | Requiere más investigación de las herramientas |
| Spaced repetition sofisticado | Primero validar que la sesión básica funciona |
| Modo offline en móvil | El PC siempre está disponible en casa |

### Criterios de avance a V2

- Usé el MVP diariamente durante 6 semanas sin fricción técnica
- WPM mejoró al menos 15 puntos
- El análisis fonético detecta correctamente mis errores en > 80% de los casos

---

## 7. Riesgos

| Riesgo | Probabilidad | Impacto | Mitigación |
|---|---|---|---|
| El análisis acústico no funciona bien en CPU lenta | Media | Alto | Usar Whisper API en MVP; WhisperX local en V2 |
| Claude da feedback pedagógicamente incorrecto | Baja | Alto | Evals contra casos conocidos antes de usar en producción |
| Me aburro y dejo de usarlo | Media | Crítico | La hoja de trabajo y el panel de apoyo son las features anti-abandono |
| Costo de APIs supera lo esperado | Baja | Bajo | Cap de $30/mes; alerta si se supera |
| Fossilización de errores no corregidos | Media | Medio | El phoneme_log acumula errores; revisar semanalmente |

---

## Historial de revisiones

| Versión | Fecha | Cambio |
|---|---|---|
| 1.0 | Jul 2025 | Documento inicial |
