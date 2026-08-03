# PLAN VERSIÓN 1 — SpeakWise

**Objetivo de este documento:** plan de ejecución concreto para construir la primera versión funcional de SpeakWise — equivalente a **ITERACIÓN 1 del BACKLOG** ("Sesión básica funcional") — con TDD real (nada se marca hecho sin tests en verde) y todo terminando versionado en GitHub, corriendo dentro del contenedor Docker ya configurado en `C:\dev\speakwise`.

Fuente: `PRD.md`, `DESIGN.md`, `CODING_STANDARDS.md`, `BACKLOG.md`, `DEFINITION-OF-DONE.md`, `README.md`, `SETUP.md`.

---

## 0. Documentos revisados

| Documento | Qué aporta a este plan |
|---|---|
| `PRD.md` | Alcance MVP (§6), métricas de éxito (§4) — no se tocan en v1 más que como contexto |
| `DESIGN.md` | Estructura de archivos, schema SQL completo, contratos de API, interfaces de providers |
| `CODING_STANDARDS.md` | Reglas de dependencia entre capas, naming, manejo de errores, checklist de cierre por task |
| `BACKLOG.md` | ITER-1 = alcance exacto de esta v1, con DoD por task |
| `DEFINITION-OF-DONE.md` | DoD global + DoD por feature + DoD de iteración |
| `README.md` | Stack, flujo de trabajo, referencias a `EVALS.md` y `decisions/ADR-*.md` |
| `SETUP.md` | Entorno Docker ya construido en `C:\dev\speakwise` (verificado funcionando) |

---

## 1. Alcance de "Versión 1"

Versión 1 = **ITERACIÓN 1 completa del BACKLOG**: sesión de conversación guiada de 20 minutos, de punta a punta, sin fricción técnica, con corpus mínimo (top 50 lemmas), accesible desde PC y móvil.

**Fuera de alcance de v1** (quedan en `BACKLOG.md` sin tocar): análisis fonético completo (ITER-2), hoja de trabajo (ITER-3), panel de apoyo adaptativo (ITER-4), auto-ajuste/spaced repetition (ITER-5).

**Criterio de cierre de v1** (copiado de `BACKLOG.md`): EVAL-06 pasa + 5 días de uso real sin fricción técnica.

---

## 2. Huecos encontrados en la documentación

Revisando los 7 documentos en conjunto aparecieron inconsistencias y referencias a cosas que no existen. Se resuelven así en este plan:

| Hueco | Resolución |
|---|---|
| `README.md` referencia `EVALS.md` — no existe | Se crea en Fase 0, con **EVAL-02** y **EVAL-06** definidos en detalle (los únicos que cierran ITER-1). EVAL-01/03/04/05 quedan como placeholders para sus iteraciones futuras. |
| `README.md` referencia `decisions/ADR-001/002/003.md` — no existen | Fuera de alcance de v1. Se anota como deuda documental, no bloquea. |
| `CODING_STANDARDS.md` §7 menciona `providers/factory.py` — no está en el árbol de `DESIGN.md` §3 | Se agrega al árbol y se actualiza `DESIGN.md` en Fase 1 (regla propia de `CODING_STANDARDS.md`: actualizar `DESIGN.md` si cambia la estructura). |
| Quién calcula `wpm`/`fillers`: el contrato `Transcript` (DESIGN §10) sugiere que lo arma el provider, pero BACKLOG asigna esa cuenta a `acoustic.py` (servicio) — y `CODING_STANDARDS` §2 prohíbe que un provider importe `services` | **Decisión:** el provider devuelve texto + timestamps crudos de Whisper; `services/acoustic.py` calcula `wpm`/`fillers` y arma el `Transcript` final antes de devolverlo al router. Documentar en `DESIGN.md`. |
| Los documentos de planificación viven en `C:\Users\pjrob\dev\sky`, pero el código y Docker viven en `C:\dev\speakwise` | Se consolida todo en **`C:\dev\speakwise`** como único repo (Fase 0). |

---

## 3. Decisiones

1. **GitHub**: repo `speakwise`, visibilidad **pública**. ✅ Confirmado — se crea en Fase 0.
2. **Corpus (top 50 lemmas + fonemas + traducciones)**: ✅ Resuelto en Fase 2 — top 50 verbos más frecuentes (consistente con el foco en formas verbales de PRD §5), traducciones curadas a mano en `words.csv`, fonemas ARPAbet derivados programáticamente de `cmudict` en `seed.py` (no hand-authored, evita errores de transcripción manual). Chunks generados por template desde la misma fila de `words.csv`, sin `chunks.csv` separado (ver `DESIGN.md` v1.3).
3. **API keys reales**: se agregan más adelante, antes de la Fase 6. No bloquean Fase 0-5 (esas fases usan mocks).

---

## 4. Estrategia TDD

**Regla dura, pedida explícitamente:** ninguna fase ni task se marca terminada sin su suite de tests correspondiente en verde, corriendo **dentro del contenedor Docker**.

| Aspecto | Decisión |
|---|---|
| Framework | `pytest` + `pytest-asyncio` + `httpx` (`TestClient`/`AsyncClient`) + `respx` (mock de llamadas HTTP salientes a Whisper/OpenAI/Claude) |
| Dónde viven | `pyproject.toml` — nuevo extra `[project.optional-dependencies] test = [...]`, instalado también en la imagen Docker |
| Ubicación de tests | `tests/`, misma forma que `backend/` (`tests/services/`, `tests/routers/`, `tests/providers/`) |
| DB de test | SQLite en archivo temporal por sesión de test (fixture en `conftest.py`), nunca toca `speakwise.db` real. Mismo schema que `database.py` crea en producción. |
| Providers externos en tests unitarios | **Mockeados siempre** — no se gasta dinero real ni se depende de red en el ciclo normal de desarrollo |
| Test de integración real | Uno solo, marcado `@pytest.mark.integration`, excluido del run por defecto y de CI; se corre manualmente antes de un release para validar que las API keys y el flujo completo funcionan con las APIs reales |
| Ciclo por task | red (test que falla) → verde (implementación mínima) → refactor → siguiente task |
| Comando dev | `docker compose exec speakwise python -m pytest -v` (contenedor ya corriendo, con hot-reload) |
| Comando CI | `docker compose run --rm speakwise python -m pytest -v -m "not integration"` |
| Gate de BACKLOG | Un task no pasa a ✅ si `pytest` no está en verde para los tests que le corresponden |

---

## 5. Estructura de repo final

```
speakwise/                      ← raíz del repo Git (= C:\dev\speakwise)
├── .git/
├── .github/workflows/test.yml  ← CI: build imagen + pytest
├── .gitignore                  ← nuevo (.venv, __pycache__, *.db, .env, data/, *.log)
├── .dockerignore
├── .env.example
├── .env                        ← NUNCA se commitea
├── pyproject.toml              ← + extra [test]
├── Dockerfile
├── docker-compose.yml
│
├── PRD.md  DESIGN.md  CODING_STANDARDS.md  BACKLOG.md
├── DEFINITION-OF-DONE.md  EVALS.md  README.md  SETUP.md  CLAUDE.md
├── planVersion1.md             ← este documento
│
├── backend/   (estructura completa según DESIGN.md §3)
├── frontend/
├── templates/
├── corpus/
└── tests/                      ← nuevo, espejo de backend/
    ├── conftest.py
    ├── test_seed.py
    ├── services/
    ├── routers/
    └── providers/
```

---

## 6. Fases de implementación

Orden pensado para respetar la dirección de dependencias de `CODING_STANDARDS.md` §2 (`routers → services → providers → APIs externas`): de adentro hacia afuera.

### Fase 0 — Repo, CI y documentación faltante

- Copiar los 8 `.md` (incluyendo este) de `C:\Users\pjrob\dev\sky` a `C:\dev\speakwise`
- `git init` en `C:\dev\speakwise`, `.gitignore`, primer commit
- Crear repo en GitHub (según decisión §3), `git remote add`, push inicial
- Agregar extra `test` a `pyproject.toml`, actualizar `Dockerfile` para instalarlo
- Crear `tests/conftest.py`: fixture de DB temporal + fixture de `TestClient` con providers mockeados
- Crear `.github/workflows/test.yml`: en cada push/PR, build de la imagen + `pytest -m "not integration"`
- Redactar `EVALS.md` con criterios concretos de **EVAL-02** y **EVAL-06**

**DoD:** repo visible en GitHub con el primer commit, Action de CI corre (aunque no haya tests reales todavía, corre "0 tests" en verde).

---

### Fase 1 — Fundaciones (`config.py`, `database.py`, `exceptions.py`, `providers/base.py`)

**Tests primero:**
- `tests/test_config.py` — falta una env var obligatoria → `EnvironmentError` con mensaje claro; con defaults → valores correctos
- `tests/test_database.py` — `get_db()` yield-based; `PRAGMA foreign_keys` y `journal_mode=WAL` activos; todas las tablas de `DESIGN.md` §4 existen tras `db_connection()` + `CREATE TABLE`
- `tests/providers/test_base.py` — las clases abstractas no se pueden instanciar directamente; una subclase que no implemente el método abstracto falla

**Implementación:** `config.py`, `database.py` (schema completo de `DESIGN.md` §4), `services/exceptions.py` (`SpeakWiseError` y subclases), `providers/base.py` (`Transcript`, `STTProvider`, `TTSProvider`, `LLMProvider`), `providers/factory.py` (selección por env var — agregar a `DESIGN.md` §3).

**DoD:** los 3 archivos de test en verde. `DESIGN.md` actualizado con `factory.py` en el árbol y la aclaración de dónde se calculan `wpm`/`fillers`.

---

### Fase 2 — Corpus y `seed.py`

**Tests primero:**
- `tests/test_seed.py`:
  - tras correr `seed.run()`, `SELECT COUNT(*) FROM word_forms` ≥ 150
  - cada fila de `word_forms` tiene `phonemes` en formato ARPAbet no vacío y `lfc_focus` no nulo
  - `SELECT COUNT(*) FROM phonetic_patterns` == 5
  - `SELECT COUNT(*) FROM chunks` ≥ 150, cada uno con `function` y `level` no nulos
  - **idempotencia**: correr `seed.run()` dos veces no duplica filas

**Implementación:** `corpus/words.csv`, `corpus/chunks.csv`, `corpus/patterns.csv` (datos — ver decisión §3.2), `backend/seed.py`.

**DoD (= DoD de `seed.py` en `DEFINITION-OF-DONE.md`):** los 5 tests en verde.

---

### Fase 3 — Providers concretos (revisado: software libre primero)

> **Cambio de alcance respecto al plan original:** el usuario pidió explícitamente priorizar software libre en todo lo posible, y usar la alternativa paga más económica cuando haga falta contratar un servicio. Esto amplía la Fase 3 de 3 a 6 providers, y agrega el servicio `ollama` a `docker-compose.yml`. Ver `DESIGN.md` §2 (tabla de stack actualizada) y `PRD.md` (cambio de decisión Ago 2026).

> **Ajuste posterior (mismo día):** se probó levantar el servicio `ollama` en Docker Compose y el usuario indicó que la PC de desarrollo no tiene recursos para correr un modelo de 7B. Se removió `ollama` de `docker-compose.yml` y se sacó `ollama_qwen` como default de LLM — el default pasa a ser **`deepseek`** (paga, la más económica). El provider `llm_ollama.py` se mantiene en el código y sus tests, disponible por `LLM_PROVIDER=ollama_qwen` para cuando se use en otra máquina.

**Jerarquía de providers final (por variable de entorno, `providers/factory.py`):**
1. **Default — libre/local, liviano:** `whisperx_local` (faster-whisper, MIT) · `kokoro` (Kokoro-82M, Apache 2.0)
2. **Default de LLM — paga más económica:** `deepseek` (compatible con SDK de OpenAI, más barato que Claude)
3. **Disponibles por env var, no default:** `ollama_qwen` (libre pero pesado, 7B) · `whisper_api` / `openai` / `claude` (pagos, referencia para el test de integración de comparación de calidad)

**Tests (todos mockeados, sin red real ni carga de modelos pesados):**
- `tests/providers/test_stt_whisper_api.py`, `test_tts_openai.py`, `test_llm_claude.py` — providers pagos, mock con `respx`
- `tests/providers/test_llm_deepseek.py` — mock con `respx` contra `api.deepseek.com`
- `tests/providers/test_llm_ollama.py` — mock con `respx`, código y tests se mantienen aunque no sea el default
- `tests/providers/test_stt_whisperx.py`, `test_tts_kokoro.py` — mock del modelo/pipeline (no se cargan pesos reales en tests unitarios, sería lento y no determinístico)
- `tests/providers/test_factory.py` — confirma default (`whisperx_local`/`kokoro`/`deepseek`) y que `ollama_qwen` sigue funcionando si se selecciona explícitamente

**Implementación:** los 6 módulos de provider + `Dockerfile`/`pyproject.toml` actualizados para instalar el extra `local` (`faster-whisper`, `kokoro`) + `espeak-ng` como dependencia de sistema para Kokoro. Sin servicio `ollama` en `docker-compose.yml`.

**DoD:** las 9 suites en verde (46/46 tests totales del proyecto), sin llamadas reales a red ni carga de modelos en el run normal. `.env.example` con los providers libres/económicos como default.

---

### Fase 4 — `acoustic.py` (WPM + fillers)

**Tests primero:**
- `tests/services/test_acoustic.py` — con timestamps de Whisper simulados (fixture fija), `wpm` calculado coincide con el valor esperado a mano; conteo de fillers (`um`, `uh`, `eh`) correcto; función CPU-bound corre en `ThreadPoolExecutor` compartido (se verifica que no bloquea el loop con un test async)

**Implementación:** `services/acoustic.py` — llama al provider STT (vía factory), calcula `wpm`/`fillers`, arma el `Transcript` final.

**DoD (= DoD de `acoustic.py` MVP en `DEFINITION-OF-DONE.md`):** WPM y fillers correctos desde timestamps reales de Whisper; funciona con audio `.webm` de móvil (test con fixture de audio webm).

---

### Fase 5 — `curriculum.py` + `GET /api/today`

**Tests primero:**
- `tests/services/test_curriculum.py` — las 3 queries de `DESIGN.md` §7 devuelven lo esperado con datos de seed conocidos; contexto total ≤ 300 tokens (contar con tiktoken o aproximación de palabras); `difficulty` cambia según promedio de `comprehensibility` simulado
- `tests/routers/test_progress.py` — `GET /api/today` devuelve 200 y el JSON exacto del contrato en `DESIGN.md` §5; responde en < 500ms

**Implementación:** `services/curriculum.py`, `routers/progress.py` (solo `/today` en esta fase — `/panel`, `/progress`, `/stats` son de iteraciones futuras, se dejan como `501 Not Implemented` explícito, no se inventan).

**DoD:** **EVAL-02 pasa** (definido en `EVALS.md`, Fase 0). Este es uno de los dos evals de cierre de ITER-1.

---

### Fase 6 — `session.py`: `/transcribe /tutor /speak`

**Tests primero:**
- `tests/routers/test_session.py`:
  - `POST /api/transcribe` con audio de prueba → 200 + contrato JSON de `DESIGN.md` §5 (versión MVP, sin `stress_results`/`phoneme_errors`)
  - `POST /api/tutor` con transcripción + historial → 200 + respuesta de Claude (mockeado)
  - `POST /api/speak` con texto → 200 + `audio/*` stream
  - ciclo completo encadenado (fixture que simula audio → texto → Claude → TTS) en < 10s con providers mockeados con latencias realistas
  - inputs inválidos → 422 con mensaje útil (qué falló + por qué), nunca excepción sin capturar

**Implementación:** `routers/session.py` (máx. 5 líneas por handler, sin lógica de negocio — según `CODING_STANDARDS.md` §5).

**DoD (= DoD de "Sesión completa" en `DEFINITION-OF-DONE.md`):** ciclo audio → `/transcribe` → `/tutor` → `/speak` en < 10s, sesión persistida en SQLite (`sessions` table).

> **Checkpoint:** a partir de acá conviene correr una vez el test de integración real (`@pytest.mark.integration`) con las API keys puestas, para confirmar que el contrato mockeado coincide con la API real antes de seguir.

---

### Fase 7 — Frontend básico

**No es TDD en el sentido de pytest** (no hay backend que testear), pero sí verificación explícita:

- `frontend/index.html`, `frontend/app.js` (grabación de audio con Web Audio API), `frontend/styles.css`
- **Verificación manual documentada** (no automatizable sin herramientas de e2e que no están en el stack): abrir en Chrome desktop y Chrome móvil (vía `http://<IP-LAN>:8000`, firewall ya configurado), grabar y reproducir un turno completo

**DoD:** funciona en Chrome desktop y Chrome móvil (criterio literal de `BACKLOG.md`).

---

### Fase 8 — PWA básica

- `frontend/manifest.json`, `frontend/service-worker.js`

**DoD:** instalable desde Chrome móvil en iPhone y Android (verificación manual — instalar y confirmar ícono en pantalla de inicio).

---

### Fase 9 — Sesión completa (3 módulos) + EVAL-06

Integra nuclear stress + chunk del día + conversación libre en un solo flujo de 20 minutos en el frontend, usando todo lo construido en Fases 1-8.

**Tests primero:**
- `tests/routers/test_session.py` (extensión) — flujo completo simulado de sesión (múltiples turnos) no deja la DB en estado inconsistente; sesión se puede recuperar completa al final

**Verificación manual:** correr **EVAL-06** completo (definido en `EVALS.md`, Fase 0) — checklist de sesión de 20 min de principio a fin sin errores técnicos.

**DoD:** EVAL-06 pasa (segundo y último eval de cierre de ITER-1).

---

### Fase 10 — Cierre de v1

- Checklist completo de `DEFINITION-OF-DONE.md` (global + por feature de esta iteración)
- `docker compose exec speakwise python -m pytest -v` — suite completa en verde
- Commit final, tag `v1.0-mvp`, push a GitHub
- Marcar todos los tasks de ITER-1 como ✅ en `BACKLOG.md`, mover la columna del tablero
- **5 días de uso real diario sin fricción técnica** antes de considerar la iteración realmente "Hecho" (criterio explícito de `BACKLOG.md` — no es un checkbox de código, es uso real)

---

## 7. Checklist de cierre de "Versión 1"

```
□ Fase 0 a 9 completas, cada una con su suite pytest en verde dentro del contenedor
□ EVAL-02 pasa
□ EVAL-06 pasa
□ Funciona en PC Windows y accesible desde móvil por WiFi (DoD global)
□ .env.example actualizado si se agregaron variables
□ DESIGN.md actualizado (factory.py, aclaración wpm/fillers)
□ Repo en GitHub, CI en verde, tag v1.0-mvp
□ Usado en al menos 1 sesión real (DoD global) → luego 5 días seguidos (DoD de iteración)
```

---

## 8. Comandos de referencia

```powershell
# Desde C:\dev\speakwise

docker compose up -d                              # levantar el entorno
docker compose exec speakwise python -m pytest -v            # correr toda la suite
docker compose exec speakwise python -m pytest -v -k seed     # correr un subset
docker compose exec speakwise python -m pytest -v -m integration   # test de integración real (gasta API)
docker compose logs -f                              # logs en vivo
```

---

## Historial

| Versión | Fecha | Cambio |
|---|---|---|
| 1.0 | Ago 2026 | Plan inicial, cubre ITER-1 completa del BACKLOG con TDD y consolidación a GitHub |
