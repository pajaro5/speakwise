# SpeakWise

> Habla inglés para que todos te entiendan.

Tutor personal de inglés con IA. Corre en tu PC como servidor local y es accesible desde el móvil vía WiFi.

---

## Inicio rápido — 5 minutos a la primera sesión

Ver **SETUP.md** para instrucciones completas de instalación en Windows.

```bash
# Resumen (después de seguir SETUP.md)
cd C:\dev\speakwise
docker compose up -d
# Abrir http://localhost:8000
```

---

## Documentación del proyecto

| Documento | Propósito | Cambia |
|---|---|---|
| [PRD.md](./PRD.md) | Qué construimos y por qué · métricas de éxito | Rara vez |
| [DESIGN.md](./DESIGN.md) | Schema DB · contratos API · estructura de archivos | Con el código |
| [CODING_STANDARDS.md](./CODING_STANDARDS.md) | Reglas de código que el agente debe seguir | Cuando aprendemos algo |
| [EVALS.md](./EVALS.md) | Cómo saber que algo funciona antes de construirlo | Por iteración |
| [BACKLOG.md](./BACKLOG.md) | Qué construir y en qué orden | Cada semana |
| [DEFINITION-OF-DONE.md](./DEFINITION-OF-DONE.md) | Qué significa "terminado" | Cuando aprendemos algo |
| [SETUP.md](./SETUP.md) | Configurar el entorno de desarrollo en Windows | Cuando cambia el stack |
| [decisions/ADR-001.md](./decisions/ADR-001-sqlite.md) | Por qué SQLite | Nunca |
| [decisions/ADR-002.md](./decisions/ADR-002-claude-api.md) | Por qué Claude API en MVP | Nunca |
| [decisions/ADR-003.md](./decisions/ADR-003-intelligibility.md) | Por qué inteligibilidad sobre natividad | Nunca |

---

## Stack

```
Backend:    FastAPI · Python 3.11
STT (MVP):  Whisper API  →  WhisperX local (V2)
TTS (MVP):  OpenAI TTS   →  Kokoro-82M (V2)
LLM (MVP):  Claude API   →  Ollama + Qwen (V2)
Acústico:   librosa  →  librosa + Parselmouth (V2)
Fonemas:    CMU Pronouncing Dictionary
Frontend:   HTML/JS · PWA
DB:         SQLite
Deploy:     Docker · PC local · acceso móvil vía WiFi
```

---

## Flujo de trabajo

```
1. Abrir BACKLOG.md → tomar primer task ⬜ de la iteración actual
2. Consultar DESIGN.md → schema y contratos relevantes
3. Seguir CODING_STANDARDS.md mientras se programa
4. Al terminar → checklist de DEFINITION-OF-DONE.md
5. Marcar ✅ en BACKLOG.md → siguiente task
6. Viernes: revisión de 30 minutos → ¿qué aprendí? → ¿qué sigue?
```

---

## Filosofía en una línea

> El acento no es el problema. La inteligibilidad es la meta. — Munro & Derwing (1995-2020)
