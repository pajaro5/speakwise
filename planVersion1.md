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

### Fase 4 — `acoustic.py` (WPM + fillers) ✅

> **Corrección al ejecutar:** la mención original de `ThreadPoolExecutor` para esta fase no aplicaba — el cálculo de `wpm`/`fillers` es aritmética simple sobre una lista corta de timestamps, no es CPU-bound. El trabajo pesado (inferencia del modelo) ya corre en `ThreadPoolExecutor` dentro de `providers/stt_whisperx.py` (Fase 3), que es la capa correcta según `CODING_STANDARDS.md` §11.

**Tests (`tests/services/test_acoustic.py`, 9 tests):**
- `_compute_wpm`: coincide con cálculo manual, devuelve `0.0` con 0 o 1 palabra
- `_count_fillers`: detecta `um`/`uh`/etc., case-insensitive, ignora puntuación
- `transcribe_and_analyze`: arma el `Transcript` final a partir de un provider (inyectado para test, o el de `factory.py` por default); maneja transcripción vacía sin errores

**Implementación:** `services/acoustic.py` — llama al provider STT (inyectable, default = `factory.get_stt_provider()`), calcula `wpm`/`fillers` sobre los timestamps crudos, arma el `Transcript` final.

**DoD (= DoD de `acoustic.py` MVP en `DEFINITION-OF-DONE.md`):** ✅ WPM y fillers correctos desde timestamps (9/9 tests, suite completa 55/55 en verde).

---

### Fase 5 — `curriculum.py` + `GET /api/today` ✅

> **Decisión de diseño tomada al implementar (no estaba en `DESIGN.md`):** `user_progress`/`pattern_progress` están vacías el día 1. Las 3 queries usan `LEFT JOIN` + `COALESCE` para priorizar por `score`/`accuracy` real cuando existe, y caer a ordenar por `rank`/`priority` del corpus cuando no — así `/api/today` es útil desde la primera sesión, no solo después de acumular progreso. Documentado en `EVALS.md` EVAL-02 y `DESIGN.md`.
>
> **Bug real encontrado y corregido:** `sqlite3.ProgrammingError: SQLite objects created in a thread can only be used in that same thread`. FastAPI resuelve dependencias sync (`get_db`) en un thread del threadpool distinto al del handler `async def` que las consume. Fix estándar: `check_same_thread=False` en `database.py` (seguro acá porque cada request tiene su propia conexión, sin compartirla entre requests concurrentes).
>
> **Falso positivo descartado:** la respuesta JSON se veía con caracteres corruptos (`/ÉªdÊ/` en vez de `/ɪdʒ/`) al mirarla desde PowerShell — era `Invoke-WebRequest`/consola mostrando mal el UTF-8, no un bug real. Verificado leyendo la respuesta con Python dentro del contenedor antes de "arreglar" algo que no estaba roto.

**Tests (`tests/services/test_curriculum.py` + `tests/routers/test_progress.py`, 19 tests):** cold-start (sin progreso previo), exclusión de formas no vencidas, exclusión de patrones ya dominados (stage 4), prioridad por `chunk_spontaneous`, las 3 reglas de `difficulty`, contrato JSON exacto vía `TestClient`, tiempo de respuesta < 500ms con datos reales de seed, y los stubs `501` de `/panel` `/progress` `/stats`.

**Implementación:** `services/curriculum.py`, `routers/progress.py` (solo `/today` implementado — `/panel`, `/progress`, `/stats` devuelven `501 Not Implemented` explícito, son de iteraciones futuras), `main.py` monta el router antes del `StaticFiles` mount (si no, el mount en `/` captura todo primero).

**DoD:** ✅ **EVAL-02 pasa** (`EVALS.md`). Verificado además contra el servidor real corriendo, no solo tests aislados. Suite completa: 74/74.

---

### Fase 6 — `session.py`: `/transcribe /tutor /speak` ✅

> **Esta fase se hizo con TDD estricto** (pedido explícito del usuario): un test a la vez, corrido para confirmar rojo antes de escribir la implementación mínima, verde, siguiente test. 9 incrementos — algunos sí mostraron rojo real (endpoint/dependencia no existía, excepción sin manejar); otros pasaron directo porque una implementación ya escrita cubría el siguiente caso (ej. FastAPI valida `File(...)` requerido solo, o la persistencia ya cubría el test de "no duplica sesión"). Eso también es TDD válido — el test queda como guardia de regresión igual.

**Decisiones de diseño tomadas al implementar (`DESIGN.md` no las especificaba):**
- Contratos de `/tutor` y `/speak` (no tenían ejemplo JSON en `DESIGN.md` §5) — documentados ahí ahora.
- Persistencia de sesión: `/tutor` crea una fila en `sessions` si no le pasan `session_id`, o actualiza esa fila si sí — sin esto no había forma de cumplir "sesión persistida" sin inventar endpoints `/session/start` y `/session/end` que `DESIGN.md` no define.
- Manejo de errores: un `@app.exception_handler(ProviderUnavailableError)` global en `main.py` en vez de `try/except` repetido en cada handler — cumple "los routers convierten excepciones de dominio a HTTP" (`CODING_STANDARDS.md` §8) sin romper el límite de 5 líneas por handler (`CODING_STANDARDS.md` §5).

**Tests (`tests/routers/test_session.py`, 9 tests, TDD estricto):**
1. `POST /api/transcribe` → 200 + contrato JSON MVP de `DESIGN.md` §5
2. sin audio → 422 (gratis de FastAPI/Pydantic)
3. `POST /api/speak` → 200 + bytes de audio
4. `POST /api/tutor` → 200 + `{reply, session_id}`
5. la sesión queda persistida en `sessions` (verificado con `SELECT` real, no solo el response)
6. reusar `session_id` actualiza, no duplica
7. LLM caído → 503 con mensaje útil (no 500 sin manejar)
8. mismo exception handler cubre `/transcribe` (verificado explícitamente)
9. ciclo completo `/transcribe` → `/tutor` → `/speak` encadenado, con latencias simuladas realistas (2s+3s+1s), termina en < 10s

**Implementación:** `routers/session.py` (handlers ≤5 líneas), `services/tutor.py` (arma el system prompt, llama al LLM, persiste), `database.py` +`create_session`/`update_session`, `main.py` +exception handler global.

**DoD (= DoD de "Sesión completa" en `DEFINITION-OF-DONE.md`):** ✅ ciclo audio → `/transcribe` → `/tutor` → `/speak` en < 10s (real: ~6s con latencias simuladas), sesión persistida en SQLite. Suite completa: 83/83.

> **Checkpoint ✅ resuelto (Fase 7):** una vez que el usuario agregó `DEEPSEEK_API_KEY` real, se creó `tests/integration/test_real_providers.py` (marcado `@pytest.mark.integration`) y se corrió contra las APIs reales: DeepSeek corrige gramática correctamente, Kokoro genera audio real (98KB, `audio/mpeg`). El contrato mockeado coincide con el real. De paso se encontró que `python -m pytest` corría estos tests de integración por defecto (gastando la API cada vez) — se agregó `addopts = "-m 'not integration'"` en `pyproject.toml` para que queden excluidos salvo que se pidan explícitamente con `-m integration`.
>
> **Nota operativa encontrada al probar:** `docker compose restart` NO relee `.env` — las variables de entorno quedan fijadas cuando el contenedor se *crea*. Para que un cambio en `.env` tome efecto hace falta `docker compose up -d --force-recreate` (o `up -d` sin más, que igual recrea si detecta cambios). Agregado a "Comandos de referencia" (§8).

---

### Fase 7 — Frontend básico ✅ COMPLETA — Chrome desktop y Chrome móvil confirmados

> **Decisión tomada al arrancar la fase (preguntada al usuario):** el plan original decía "no es TDD en el sentido de pytest". Se ofrecieron 2 caminos — agregar Playwright para TDD real de browser, o tests de estructura/contenido vía pytest + QA manual — y se eligió la segunda por costo de recursos (Playwright es pesado, y esta PC ya mostró límites con Ollama).

**Tests con TDD estricto (`tests/frontend/test_frontend_structure.py`, 7 tests, uno a la vez con rojo confirmado):** botón de grabar existe, `index.html` carga `app.js`, tiene meta viewport, tiene áreas de transcripción/respuesta y reproductor de audio, `app.js` usa `getUserMedia`/`MediaRecorder`, `app.js` llama a los 3 endpoints de sesión. Esto valida estructura y contenido, **no comportamiento real en el navegador**.

**Verificación manual — Chrome desktop:**
- ✅ La página carga sin errores de consola, con los estilos aplicados (Claude en Chrome)
- ✅ El botón dispara `getUserMedia` correctamente
- ✅ **Ciclo completo confirmado por el usuario con micrófono real**: grabar → transcribir → corrección del tutor (DeepSeek) → audio de respuesta (Kokoro) — funciona de punta a punta
- ✅ **Chrome móvil confirmado por el usuario por WiFi**: después del flag de Chrome (ver bug 2 abajo), la grabación funciona en el celular también

**Implementación:** `frontend/index.html`, `frontend/app.js` (Web Audio API + MediaRecorder + fetch a `/transcribe /tutor /speak` encadenados), `frontend/styles.css`.

> **Bug 1 (encontrado en desktop sin API key):** faltaba `DEEPSEEK_API_KEY` en `.env`, y esa falla se caía como **500 sin manejar** — el `@app.exception_handler(ProviderUnavailableError)` de Fase 6 no cubría `EnvironmentError` (la excepción que lanza `require()` en `config.py`). Además `app.js` nunca revisaba `response.ok`. Corregido con TDD: agregado `@app.exception_handler(EnvironmentError)` en `main.py`, `app.js` ahora muestra `Error: <mensaje>` en el status. Confirmado: `POST /api/tutor` sin key ahora devuelve `503` con mensaje claro en vez de 500.
>
> **Bug 2 (encontrado probando en el celular por WiFi):** el botón de grabar no hacía nada, sin popup de permiso ni error visible. Causa real: `navigator.mediaDevices` **solo existe en contextos seguros** (HTTPS o `localhost`) — por WiFi se accede vía `http://192.168.1.4:8000`, un origen no seguro, así que Chrome ni siquiera expone la API (no es que el permiso se deniegue, la función no existe). El click handler tampoco tenía manejo de errores, así que el fallo quedaba invisible. Corregido con TDD: chequeo explícito de `navigator.mediaDevices` con mensaje claro en pantalla, y el click handler ahora atrapa cualquier error. **Solución real para probar sin HTTPS:** habilitar `chrome://flags/#unsafely-treat-insecure-origin-as-secure` en el celular con la IP de la PC — es una limitación de seguridad del navegador, no algo resoluble desde el servidor.

**DoD (criterio literal de `BACKLOG.md`: "funciona en Chrome desktop y Chrome móvil"):** ✅ **CUMPLIDO.** Chrome desktop y Chrome móvil confirmados de punta a punta por el usuario, con micrófono real y providers reales (DeepSeek + Kokoro). 95/95 tests.

---

### Fase 8 — PWA básica ✅ COMPLETA (Android confirmado; iPhone fuera de alcance — usuario no tiene el dispositivo)

**Tests con TDD estricto (`tests/frontend/test_pwa.py`, 5 tests, uno a la vez con rojo confirmado):** `manifest.json` válido con campos requeridos (`name`, `short_name`, `start_url`, `display`); tiene íconos 192x192 y 512x512 que existen en disco; `index.html` linkea el manifest; `service-worker.js` tiene un listener de `fetch` (requisito de Chrome para instalabilidad); `app.js` registra el service worker.

**Implementación:** `frontend/manifest.json` (con `frontend/icon.svg` como ícono — SVG en vez de PNG, evita necesitar generación de imágenes binarias; Chrome acepta SVG para manifests de PWA), `frontend/service-worker.js` (cachea el app shell en `install`, sirve desde caché con fallback a red en `fetch`, **excluye `/api/*` explícitamente** para no cachear respuestas de transcribe/tutor/speak), meta tags de iOS en `index.html` (`apple-touch-icon`, `apple-mobile-web-app-capable`).

**Verificación en vivo (Claude en Chrome, no solo tests):** manifest se lee correctamente vía `fetch`, service worker registrado con el scope correcto (`http://localhost:8000/`), sin errores ni warnings en consola tras recargar la página.

**DoD (criterio literal de `BACKLOG.md`: "instalable en iPhone y Android desde Chrome"):** ✅ **Android confirmado por el usuario** — instaló la app y el ícono aparece en la pantalla de inicio. **iPhone queda fuera de alcance**: el usuario no tiene el dispositivo, y de todos modos en iOS la instalación de PWA se hace desde Safari, no Chrome (limitación de la plataforma, no del código). Se documenta como límite conocido, no como pendiente bloqueante — mismo criterio aplicado a Chrome móvil sin teléfono físico en Fase 7.

---

### Pausa deliberada antes de Fase 9 (Ago 2026)

El usuario planteó una preocupación válida: construir 2 módulos de UI nuevos (nuclear stress, chunk del día) basados solo en la descripción del PRD, sin haber usado todavía lo que ya existe, es programar a ciegas — exactamente el riesgo que el propio `BACKLOG.md` previene con su criterio de "En uso" (5 días de uso real antes de dar algo por "Hecho").

**Decisión:** en vez de construir los módulos separados de Fase 9, se conectó el motor de currículum (`curriculum.py`, Fase 5 — ya construido pero nunca usado) al tutor conversacional. Ahora `services/tutor.py` arma el system prompt dinámicamente con `curriculum.build_todays_plan()`: incluye el chunk del día y las palabras a reforzar, e instruye al LLM a guiarlas hacia la conversación de forma natural. Esto entrega valor real de vocabulario dirigido sin construir UI nueva — validación barata antes de invertir en módulos separados.

**Tests (`tests/services/test_tutor.py`, 2 tests, TDD estricto):** el system prompt enviado al LLM incluye el chunk del día y al menos una de las formas a reforzar (verificado con un provider fake que captura el prompt real).

**Hallazgo real de contenido, encontrado probando contra DeepSeek real:** el chunk generado por template para el verbo "be" es gramaticalmente raro — `"I be this every day."` no es inglés estándar (el propio tutor lo marcó como "informal" en su respuesta). Es una debilidad de los templates de `seed.py` (Fase 2): `"I {form} this every day"` no funciona bien para verbos irregulares como "be". **Pendiente, no bloqueante**: revisar/curar los templates de chunks, sobre todo para "be"/"have"/"do".

**Actualización — el usuario retomó Fase 9 explícitamente** después de ver la tabla completa de funcionalidad construida vs. pendiente. Se construyó con TDD, en incrementos backend → frontend.

---

### Fase 9 — Sesión completa (3 módulos) + EVAL-06 ✅ backend+frontend construidos — verificación manual con micrófono pendiente

**Backend (TDD, 6 tests nuevos):**
- `database.py`: `upsert_pattern_progress` (cuenta exposición al patrón, sin scoring de precisión — eso es ITER-2), `mark_chunk_used` (actualiza `sessions.chunk_used`/`chunk_produced`)
- `services/log.py`: `handle_log_event` — dispatcher para `POST /api/log` (diseñado recién, `DESIGN.md` solo tenía el nombre)
- `POST /api/session/start` (nuevo endpoint, no estaba en `DESIGN.md`): crea la sesión *antes* de los módulos, para que los 3 compartan `session_id` desde el principio en vez de que `/api/tutor` cree uno recién en conversación libre

**Frontend (TDD estructural, 11 tests nuevos):** `index.html` reestructurado en 3 secciones (`#module-1/2/3`) + pantalla de inicio; `app.js` reescrito — botón "Empezar sesión" trae `/api/today` + `/api/session/start`, popula módulo 1 (patrón fonético: escuchar ejemplos vía TTS + grabar intento con auto-stop a los 4s) y módulo 2 (chunk: escuchar + usarlo en una oración con auto-stop a los 5s, feedback automático de si se detectó el chunk), módulo 3 reusa el flujo de conversación libre ya construido (Fase 6/7) pero ahora con `session_id` real compartido en vez de `null`.

**2 bugs reales encontrados probando en Chrome real (Claude en Chrome), ambos corregidos con TDD antes de dar por terminada la fase:**
1. Los botones de grabar de módulo 1/2 iniciaban la grabación pero nunca la detenían (sin lógica de stop) — arreglado con auto-stop por tiempo, apropiado para grabaciones cortas de una frase.
2. **El service worker (Fase 8) servía una versión vieja del HTML** — cache-first significa que, tras este mismo deploy, el navegador seguía mostrando la pantalla de Fase 8 aunque el servidor ya tenía la de Fase 9. Cambiado a network-first (intenta red primero, cache solo como fallback offline) + `CACHE_NAME` bump a `v2` para invalidar lo viejo + `skipWaiting()`/`clients.claim()` para que las actualizaciones futuras apliquen sin tener que cerrar todas las pestañas. Esto habría afectado tu instalación real en Android en cada deploy futuro si no se corregía.

**Verificado en vivo, de punta a punta (sin micrófono real — eso sigue siendo verificación humana):** `/api/today` trae el plan correctamente, módulo 1 se puebla y registra práctica (`pattern_progress.sessions_practiced` confirmado en la DB real), módulo 2 registra el chunk usado (`sessions.chunk_used`/`chunk_produced` confirmado en la DB real), módulo 3 recibe el `session_id` compartido.

**DoD:** ⚠️ **Parcial.** Todo el código y la lógica confirmados funcionando contra la DB y APIs reales. Falta la verificación manual con micrófono real de los 3 módulos encadenados (EVAL-06 completo) — mismo patrón que Fases 7/8.

Suite completa: 121/121.

---

### Fase 9.1 — 4 bugs reales de la primera sesión completa con micrófono real ✅

El usuario probó la sesión de punta a punta con micrófono real (primera vez que EVAL-06 se ejerce completo) y reportó 4 problemas concretos. Corregidos uno por uno con TDD estricto (red confirmado antes de implementar cada uno):

1. **"El Grabar-parar no es intuitivo"** — los botones no dejaban claro si estaban grabando o no. Arreglado: texto e ícono del botón cambian según el estado (🔴 "Grabando..." deshabilitado en módulos 1/2 con auto-stop; "⏹️ Detener" en módulo 3). Test: `test_app_js_gives_clear_recording_state_feedback`.
2. **"Siempre debe dar el feedback en inglés"** — el tutor mezclaba español en las correcciones. Arreglado: instrucción explícita en `BASE_SYSTEM_PROMPT` (`services/tutor.py`) — "respondé siempre en inglés, nunca en español". Test: `test_tutor_system_prompt_requires_english_only_replies`.
3. **"En la tercera parte debe mostrar palabras para usar como sugerencia (me quedo en blanco)"** — módulo 3 (conversación libre) no mostraba ningún apoyo léxico. Arreglado: panel `#word-suggestions` en `index.html`, poblado en `startSession()` desde `todaysPlan.week_words` (dato que ya se traía pero no se usaba). No es el panel completo de apoyo adaptativo (eso es ITER-4) — solo una lista simple para no bloquear la conversación. Test: `test_index_html_has_word_suggestions_panel_in_module_3`.
4. **"En la parte dos, el ejemplo no da contexto, no sé qué decir"** (el chunk de "be": `"I be this every day."`) — confirmado el hallazgo ya anotado en Fase 8: el template genérico de `seed.py` asume verbos de acción con objeto directo, pero "be" es cópula y no encaja en ningún template (`"I be this every day"`, `"I'm being it right now"`, `"Yesterday I was it"` — los 4 tenses salían mal). Arreglado con `IRREGULAR_CHUNKS` en `backend/seed.py`: chunks curados a mano por tense para "be" (`"Be careful with that."`, `"She is happy today."`, `"I'm being careful with this."`, `"Yesterday I was tired."`), con contexto claro de uso. `seed_chunks()` ahora actualiza (`UPDATE`) chunks existentes en vez de solo insertar-si-falta, para que un re-seed corrija datos ya poblados. Test nuevo: `tests/test_seed.py::test_be_chunks_are_grammatical`.

**Bug de infraestructura encontrado de paso, no reportado por el usuario pero real:** `pyproject.toml` no está en bind-mount (a diferencia de `backend/`, `frontend/`, `tests/`, `corpus/`) — sus cambios solo aplican con rebuild de imagen. El fix de Fase 6 al `addopts = "-m 'not integration'"` (para no gastar créditos de API en cada run de tests) nunca llegó a la imagen corriendo — quedó solo en el host. Confirmado corriendo la suite completa sin filtro, que gastó una llamada real a DeepSeek. Corregido con `docker compose build` + recreate.

Suite completa tras los 4 fixes: 120/120 (nuevo test de seed sumado).

**Tests primero:**
- `tests/routers/test_session.py` (extensión) — flujo completo simulado de sesión (múltiples turnos) no deja la DB en estado inconsistente; sesión se puede recuperar completa al final

**Verificación manual:** correr **EVAL-06** completo (definido en `EVALS.md`, Fase 0) — checklist de sesión de 20 min de principio a fin sin errores técnicos.

**DoD:** EVAL-06 pasa (segundo y último eval de cierre de ITER-1).

---

### Fase 9.2 — Apoyo a conversación libre: 3 categorías (pedido del usuario tras probar el fix #3 de Fase 9.1) ✅

El panel simple de Fase 9.1 (lista plana de `week_words`, ej. "be, is, being, was, been" — formas del mismo lemma, poco útil como sugerencia) se reemplaza por 3 categorías concretas que el usuario pidió explícitamente:

1. Frases para iniciar la conversación
2. Conectores de ideas (ej. "for example", "between")
3. Temas para la conversación (ya existía como `topic_options`, ahora se muestra)

**Backend (TDD):** `curriculum.py` — nuevos pools curados `CONVERSATION_STARTERS` (8 frases) y `LINKING_WORDS` (10 conectores), mismo patrón que `TOPIC_POOL` (sin tabla propia en el schema). `build_todays_plan()` agrega `conversation_starters` y `linking_words` (3 al azar c/u) al contrato de `/api/today`. Tests actualizados: `test_build_todays_plan_has_full_contract_shape` (curriculum) y `test_today_returns_200_with_full_contract` (router).

**Frontend (TDD estructural):** `index.html` — panel `#word-suggestions` reemplazado por `#conversation-starters`/`#linking-words`/`#topic-suggestions` dentro de `#conversation-support`. `app.js` — poblados en `startSession()` desde los 3 nuevos campos del plan. Test: `test_index_html_has_conversation_support_categories_in_module_3`.

**Verificado en vivo (Chrome, `startSession()` real contra la API real):** `linkers: "also, on the other hand, by the way"`, `starters: "So, how's it going? · So, tell me about your day. · Guess what happened to me today."`, `topics: "un problema que resolviste · algo que aprendiste hace poco · algo que viste"`.

`DESIGN.md` actualizado con el nuevo contrato de `/api/today`. Sigue sin ser el panel adaptativo de ITER-4 (sin fading logic, sin tracking de `prompts_used`) — apoyo estático, alcance mínimo para no bloquear la conversación.

Suite completa: 124/124 (2 de integración deseleccionados).

---

### Fase 9.3 — 3 observaciones probando módulo 1 (patrón fonético) ✅

El usuario probó módulo 1 tras el fix de Fase 9.2 y reportó 3 problemas concretos, corregidos con TDD:

1. **"Al dar clic en 'Escuchar ejemplos' el botón debe deshabilitarse, tarda un poco y sigo presionando varias veces"** — el TTS real (Kokoro) tarda unos segundos en generar el audio y no había ningún feedback de carga. Arreglado con `playTextWithButton(text, btn)` en `app.js`: deshabilita el botón al hacer clic, lo reactiva en un `finally` cuando `audio.play()` resuelve (arranca la reproducción). Aplicado a los dos botones "Escuchar" (módulo 1 y módulo 2 — mismo bug, mismo código compartido). Test: `test_app_js_disables_listen_buttons_while_playing_audio`.
   - **Decisión de diseño, con vuelta atrás real:** la primera versión esperaba al evento `ended` (reactivar solo cuando termina de sonar, no solo cuando arranca) para evitar además reproducciones superpuestas. Al verificar en vivo con Claude en Chrome, la pestaña en background (`document.visibilityState === "hidden"`) nunca cargaba los datos del `<audio>` (`readyState` se quedaba en 0 indefinidamente) — el botón quedaba deshabilitado para siempre. Dado que esta app es de uso móvil (PWA), un usuario real bloqueando la pantalla o cambiando de app mientras carga el TTS podría quedar en la misma situación. Se revirtió a la versión más simple y seguro: reactivar en cuanto arranca la reproducción, no cuando termina — resuelve el problema reportado sin el riesgo de un botón roto permanentemente.
2. **"Quiero que muestre cómo debo pronunciar"** — el patrón solo mostraba la regla en español (que ya incluye el IPA embebido en el texto, ej. "= /ɪdʒ/") y la lista de palabras de ejemplo, sin destacar la pronunciación. `phonetic_patterns.rule_ipa` ya existía en el schema pero `_pattern_of_the_day()` no lo seleccionaba. Arreglado: se agrega `rule_ipa` al contrato de `pattern_focus`, mostrado en negrita como "Pronunciación: **/ʃən/**" en módulo 1. Tests: `test_pattern_of_the_day_cold_start_picks_priority_1` (shape actualizado), `test_index_html_has_pattern_pronunciation_element`.
3. **"En todas las pruebas siempre iniciamos con lo mismo, age idge, ¿eso es correcto?"** — no del todo. `_pattern_of_the_day()` ordena por `accuracy` (siempre 0.0, sin scoring real hasta ITER-2) y `priority` — como tres patrones comparten `priority = 1`, el desempate era determinista y siempre caía en el mismo (el primero insertado por `seed.py`). `sessions_practiced` se registraba (`pattern_progress.sessions_practiced`) pero no se usaba para ordenar. Arreglado agregando `COALESCE(pp.sessions_practiced, 0) ASC` como criterio de desempate intermedio — mismo patrón que `_chunk_of_the_day()` ya usaba con `spontaneous_uses`. Verificado en la DB real del usuario: con práctica previa registrada para "-age/-idge" (de la sesión real que ya corrió), el patrón del día pasó a ser "-tion/-sion". Test: `test_pattern_of_the_day_prefers_least_practiced`.

`DESIGN.md` actualizado con `rule_ipa` en el contrato de `pattern_focus`.

**Verificado en vivo (Chrome):** IPA visible en pantalla ("Pronunciación: **/ʃən/**"), rotación de patrón confirmada contra la DB real. La verificación del ciclo completo deshabilitar→reproducir→reactivar del botón no pudo confirmarse con certeza vía automatización — la pestaña de Claude en Chrome no queda "visible" (`document.visibilityState`) para la extensión, así que el elemento `<audio>` nunca cargaba datos en ese contexto. El código sigue el patrón estándar (deshabilitar en el click, reactivar en `finally` tras `await audio.play()`) y no depende de nada específico del entorno de test — pendiente de que el usuario lo confirme con uso real.

Suite completa: 127/127 (2 de integración deseleccionados).

---

### Fase 9.4 — 3 ejemplos de uso del chunk del día (módulo 2) ✅

El usuario probó módulo 2 con el chunk "Be careful with that." (function: imperative) y pidió mostrar 3 ejemplos de uso: una oración simple, un párrafo, y una "conversación".

**Decisión de diseño:** curar a mano 3 ejemplos por chunk no escala — hay 200 chunks (50 lemmas × 4 tenses). Se generan bajo demanda con el LLM configurado (DeepSeek), reusando la misma abstracción `LLMProvider` que ya usa el tutor — consistente con la prioridad de software libre/pago más barato ya establecida en el proyecto.

**Backend (TDD):**
- `services/chunk_examples.py` (nuevo) — `get_chunk_examples(llm, chunk, function)`: prompt le pide al LLM devolver JSON `{sentence, paragraph, conversation}`; si no es JSON válido o falta un campo, `ProviderUnavailableError`. Tests: `tests/services/test_chunk_examples.py` (4 tests — shape, contenido enviado al LLM, JSON inválido, campo faltante).
- `POST /api/chunk-examples` (nuevo, `routers/session.py`) — reusa el handler de `ProviderUnavailableError`→503 ya existente. Tests en `tests/routers/test_session.py` (2 tests).

**Frontend (TDD estructural):** `index.html` — `#chunk-examples-status` (feedback de carga) + 3 elementos (`#chunk-example-sentence/paragraph/conversation`) dentro de módulo 2. `app.js` — `loadChunkExamples()` se llama automáticamente al entrar a módulo 2 (click en "Siguiente →" desde módulo 1), sin bloquear el resto del módulo (que ya tiene chunk/función desde `/api/today`); maneja error internamente, no puede rechazar sin capturar. Tests: `test_index_html_has_chunk_examples_elements`, `test_app_js_loads_chunk_examples_when_entering_module_2`.

**Verificado en vivo contra DeepSeek real (Chrome, pestaña en primer plano):** feedback "Cargando ejemplos..." visible de inmediato, ejemplos recibidos ~12s después, coherentes y en contexto:
- Oración: "Be careful with that glass; it's fragile."
- Párrafo: sobre llevar una bandeja caliente, terminando en "Just take it slowly."
- Conversación: diálogo de 3 líneas sobre cargar una caja pesada.

`DESIGN.md` actualizado con el contrato de `POST /api/chunk-examples`.

Suite completa: 135/135 (2 de integración deseleccionados).

---

### Fase 9.5 — 4 ajustes de Fase 9.4 probando módulo 2 en vivo ✅

El usuario probó los ejemplos del chunk "Be careful with that." y reportó 4 problemas, corregidos con TDD:

1. **"Todo debe estar en inglés"** — el `SYSTEM_PROMPT` ya pedía inglés pero no prohibía explícitamente mezclar español. Reforzado: "el contenido de los 3 campos tiene que estar TOTALMENTE en inglés — nada de español". Test: `test_system_prompt_forbids_spanish`.
2. **"En el ejemplo de conversación se ve el backslash-n literal"** — el LLM a veces devuelve el JSON con el backslash doblado (`\\n` en vez de `\n`), así que `json.loads` decodifica un backslash+n literal en vez de un salto de línea real. Arreglado con normalización defensiva en `get_chunk_examples()` (`.replace("\\n", "\n")`) + CSS `white-space: pre-line` en los elementos de párrafo/conversación (necesario de todos modos para que saltos de línea reales se vean, sea cual sea la causa). Test: `test_get_chunk_examples_normalizes_escaped_newlines`.
3. **"Usemos íconos para oración simple, párrafo y conversación"** — reemplazados los labels en español por ✏️/📄/💬. Test: `test_index_html_chunk_examples_use_icons_not_spanish_labels`.
4. **"El chunk debe aparecer siempre en negritas"** — interpretado como: siempre, incluyendo dentro de los 3 ejemplos generados, no solo en el display principal. `chunk-text` envuelto en `<strong>` (siempre es el chunk exacto). Para los ejemplos generados se agregó `boldChunkOccurrences(text, chunk)` en `app.js`: escapa HTML, busca el chunk (case-insensitive) dentro del texto y lo envuelve en `<strong>`, usando `.innerHTML` en vez de `.textContent` — con `escapeHtml()` aplicado antes para evitar XSS sobre contenido generado por el LLM.
   - **Bug real encontrado verificando en vivo:** el LLM a veces sigue la oración después del chunk sin el punto final (ej. "Be careful with that **glass vase**...", no "Be careful with that.**glass vase**"), así que el match exacto (con el punto incluido) no encontraba nada en el párrafo. Arreglado ignorando puntuación final del chunk al buscar coincidencias (`chunk.trim().replace(/[.!?]+$/, "")`). Test: `test_app_js_bolding_ignores_trailing_punctuation`.

**Verificado en vivo contra DeepSeek real:** las 3 categorías ahora resaltan el chunk correctamente, incluso cuando el LLM lo integra en una oración más larga sin el punto final.

Suite completa: 141/141 (2 de integración deseleccionados).

---

### Fase 9.6 — Interfaz completa en inglés ✅

El usuario pidió que toda la app esté en inglés: botones, títulos, mensajes de estado/error. Antes de tocar código se preguntó el alcance exacto vía `AskUserQuestion`, porque incluía una decisión de producto real: ¿también las explicaciones de reglas de pronunciación (`rule_es`, ej. "Termina en -age o -idge = /ɪdʒ/, la E no suena"), que están en español a propósito como técnica pedagógica (explicar la regla nueva en el idioma nativo)? El usuario eligió **solo la interfaz** — `rule_es` queda en español.

**Cambios:** `index.html` (`lang="es"` → `lang="en"`, títulos de los 3 módulos, texto de todos los botones, labels del panel de apoyo de módulo 3) y `app.js` (todos los mensajes de `statusEl`/`chunkFeedbackEl`/`chunkExamplesStatusEl`, labels de grabación por modo, mensaje de error de micrófono, log de consola del service worker).

**Test de regresión (TDD):** `test_ui_text_is_in_english_not_spanish` — lista de 20 marcadores de texto en español que existían antes, verifica que ninguno esté en `index.html`/`app.js` (no en las reglas de pronunciación de la DB, que no se tocan). RED confirmado con el texto viejo, GREEN tras traducir.

**Verificado en vivo (Chrome):** botones, títulos y mensajes en inglés; `pattern_rule` sigue mostrando la explicación en español, sin cambios.

Suite completa: 142/142 (2 de integración deseleccionados).

---

### Fase 9.7 — Resaltar sílabas/letras en las palabras de ejemplo de módulo 1 ✅

El usuario notó que en "sílabas elididas" las palabras de ejemplo no dejaban claro cuál sílaba no se pronuncia. Pregunta exploratoria respondida primero con una recomendación (curar a mano qué parte resaltar por palabra, ya que derivarlo del CMU dict es un problema real de alineación grafema-fonema) — el usuario la aprobó y se generalizó a los 5 patrones, no solo el de sílabas elididas.

**Diseño:** markup inline en el campo `family` de `patterns.csv` — `~x~` para letra/sílaba muda (tachado), `*x*` para parte resaltada/pronunciada distinto a como se escribe pero no muda (highlight). Sin cambio de schema: `family` ya se guardaba como JSON de texto libre.

- `-age/-idge`: resalta el sufijo (`aver*age*`)
- `-tion/-sion`: resalta el sufijo (`na*tion*`)
- `sílabas elididas`: tacha la vocal muda (`diff~e~rent`)
- `letras mudas kn-/wr-`: tacha la consonante muda (`~k~now`)
- `schwa`: resalta la vocal átona reducida (`*a*bout`, `b*a*nan*a*`)

**Backend (TDD):** `corpus/patterns.csv` actualizado con el markup. `seed_patterns()` tenía el mismo bug que tuvieron los chunks de "be" (Fase 9.1): si el pattern ya existía, no actualizaba `family`/`rule_es`/`rule_ipa` — cambiado a `UPDATE` para que un re-seed corrija DBs ya pobladas. Tests: `test_pattern_family_words_have_marked_syllables`, `test_reseeding_updates_pattern_family_markup`.

**Frontend (TDD estructural):** `app.js` — `renderMarkedWord()`/`renderPatternFamily()` parsean el markup a `<s>`/`<mark>`; `stripMarkup()` saca los símbolos antes de mandar el texto al TTS (si no, Kokoro leería los `~`/`*` literales). CSS: `<mark>` amarillo, `<s>` gris con tachado rojo. Test: `test_app_js_renders_pattern_family_markup`.

**Verificado en vivo (Chrome):** tachado visible en "different, chocolate, vegetable, camera, family" (letra muda en rojo), resaltado amarillo en "average, manage, village, damage, package" (sufijo), y confirmado que el botón "Listen to examples" le manda al TTS el texto limpio sin símbolos.

Suite completa: 145/145 (2 de integración deseleccionados).

---

### Fase 9.8 — Detección de chunk fallaba por puntuación + pedir repetir si no se detecta ✅

El usuario grabó "Be careful with that" correctamente pero la app dijo "I didn't detect the exact chunk, but let's keep going" y lo dejó avanzar igual.

**Bug real (backend):** `log_chunk_used()` comparaba el chunk completo (`"Be careful with that."`, con punto final, tal como está en la DB) contra el transcript de Whisper (que normalmente no incluye el punto) con substring exacto — mismo problema que ya se había corregido en el resaltado del frontend (Fase 9.5), esta vez en la lógica de detección real que determina el feedback. Arreglado ignorando puntuación final del chunk antes de comparar (`re.sub(r"[.!?]+$", "", chunk)`). Test: `test_log_chunk_used_ignores_trailing_punctuation_mismatch`, reproduce el caso exacto reportado.

**Cambio de UX (frontend):** cuando no se detecta el chunk, la app ya no dejaba avanzar con un mensaje genérico — ahora pide repetir la grabación y no muestra el botón "Next" hasta que se detecte. El botón de grabar ya queda disponible de nuevo (mismo estado que después de cualquier grabación), así que repetir es solo volver a tocarlo. Test: `test_app_js_chunk_recording_requires_retry_when_not_detected`.

**Verificado en vivo contra la API real:** el caso exacto reportado ("Be careful with that." vs. transcript "Be careful with that") ahora devuelve `produced: true`; simulado el caso de no-detección, el botón "Next" queda oculto y aparece el mensaje de repetir.

Suite completa: 147/147 (2 de integración deseleccionados).

---

### Fase 9.9 — Módulo 3 rediseñado como chat estilo WhatsApp ✅

El usuario pidió que módulo 3 (conversación libre) tenga look and feel de chat: grabar, ver la respuesta, y que la conversación avance hacia abajo — no un solo par de elementos de texto que se pisan en cada turno (comportamiento anterior desde Fase 6/7).

**Frontend (TDD estructural):** `index.html` — `#transcript`/`#tutor-reply`/`#tutor-audio` (fijos) reemplazados por `#chat-log` (contenedor scrolleable). `app.js` — `appendChatMessage(text, sender, audioUrl)` crea una burbuja (`div.chat-bubble.chat-user` o `.chat-tutor`), la agrega al log y hace scroll automático al final (`chatLogEl.scrollTop = chatLogEl.scrollHeight`); `handleFreeConversationRecording()` ahora agrega una burbuja de usuario tras transcribir y una del tutor (con su audio adjunto) tras la respuesta, en vez de pisar `transcriptEl`/`tutorReplyEl`. CSS estilo WhatsApp: fondo beige del chat, burbujas verdes alineadas a la derecha (usuario), blancas a la izquierda (tutor). Tests: `test_index_html_has_chat_log_area` (reemplaza los tests viejos de `#transcript`/`#tutor-reply`/`#tutor-audio`), `test_app_js_free_conversation_renders_chat_bubbles`.

**Verificado en vivo (Chrome):** burbujas renderizadas correctamente (verde/usuario a la derecha, blanco/tutor a la izquierda), scroll automático confirmado forzando overflow (`scrollTop + clientHeight >= scrollHeight` tras agregar mensajes).

Suite completa: 147/147 (2 de integración deseleccionados).

---

### Fase 9.10 — Markdown literal en el chat y leído en voz alta por el TTS ✅

El usuario reportó que módulo 3 mostraba texto tipo `**"phoneme"**` sin renderizar (asteriscos literales en la burbuja del chat), y que el TTS después leía "asterisk, asterisk phoneme" en voz alta — el LLM (DeepSeek) a veces devuelve markdown, pero la app trata la respuesta como texto plano en ambos lugares.

**Fix de raíz (backend):** `BASE_SYSTEM_PROMPT` en `services/tutor.py` ahora prohíbe explícitamente markdown, explicando el motivo (se muestra como texto plano y se lee con TTS). Test: `test_tutor_system_prompt_forbids_markdown`.

**Defensa extra (frontend):** `stripMarkdown()` (nuevo, `app.js`) saca `**negrita**`, `*cursiva*`, `` `código` `` y `__negrita__` con regex simple, aplicado a la respuesta del tutor antes de guardarla en `history`, mostrarla en el chat, y mandarla a `/api/speak` — una sola limpieza, no en cada lugar por separado. Test: `test_app_js_strips_markdown_from_tutor_reply`.

**Verificado en vivo contra DeepSeek real:** le pedí explícitamente que use negrita para forzar el caso — el modelo directamente se negó a usar markdown ("I will not use any markdown formatting..."), confirmando que el prompt reforzado funciona. `stripMarkdown()` verificado por separado con texto sintético con los 4 tipos de markdown mezclados.

Suite completa: 169/169 (2 de integración deseleccionados).

---

### Fase 9.11 — Whisper transcribía en otro alfabeto (idioma sin fijar) ✅

El usuario reportó en módulo 1: `I heard: "Πιλάτσο!"` — griego, sin relación con nada de lo que pudo haber dicho. Preguntó si de verdad hablaba tan mal.

**Bug real, no el usuario:** ni `WhisperXLocalProvider` (faster-whisper, local) ni `WhisperAPIProvider` (OpenAI, alternativa paga) fijaban el idioma esperado — Whisper adivina el idioma hablado a partir del propio audio. En grabaciones cortas (módulo 1 tiene auto-stop a los 4s) el modelo tiene poca señal para adivinar bien, y a veces le erra por completo, devolviendo texto en un alfabeto totalmente distinto. Esta app es exclusivamente de inglés — no hay nada que adivinar.

**Fix:** `language="en"` fijo en ambos providers (`model.transcribe(..., language="en")` en faster-whisper; `language="en"` en el request a la API de OpenAI). Tests: `test_transcribe_pins_language_to_english` en ambos `tests/providers/test_stt_*.py`.

**Verificado en vivo contra el pipeline real:** audio TTS real de "average" → `{"text": "Average.", ...}`, transcrito correctamente en inglés.

Suite completa: 189/189 (3 de integración deseleccionados).

---

### Fase 9.12 — Nombrar las palabras mal acentuadas + caché HTTP de app.js ✅

El usuario probó módulo 1 con el fix de ITER-2 (stress detection) y reportó: "Stress correct on 2/4 word(s) — debe decirme cuáles son las que están mal".

**Fix:** `handlePatternRecording()` ahora arma la lista de palabras incorrectas (`results.filter((r) => !r.correct).map((r) => r.word)`) y las nombra en el mensaje: `"Stress correct on 1/3 word(s) — check: average, village."`. Si todas están bien, mensaje distinto sin la parte de "check". Test: `test_app_js_pattern_recording_names_the_incorrect_words`.

**Bug de infraestructura encontrado de paso verificando en vivo, no reportado por el usuario:** al probar el fix en Chrome, ni un reload normal ni limpiar el service worker (ya arreglado en Fase 8) hacían que se cargara el `app.js` nuevo — hizo falta un hard-refresh (Ctrl+Shift+R) para que se notara el cambio. Investigado: `StaticFiles` de Starlette no manda `Cache-Control`, así que el navegador puede servir un archivo viejo desde su caché HTTP normal sin siquiera intentar revalidar, según su heurística de frescura — un problema distinto y más profundo que el de Fase 8 (que era del *service worker*, ya en network-first). Esto significa que un usuario real podría no ver los cambios de un deploy nuevo ni con una recarga simple de la página, solo con hard-refresh (que la mayoría no sabe hacer, y no existe en un PWA instalado en el celular). Arreglado con `NoCacheStaticFiles` (subclase de `StaticFiles` en `main.py`) que agrega `Cache-Control: no-cache` a cada respuesta — fuerza revalidar (ETag/Last-Modified) en cada carga, sigue siendo barato (304 si no cambió) pero nunca sirve algo viejo sin chequear primero. Test: `test_static_files_are_served_with_no_cache_header`.

**Verificado en vivo:** mensaje con palabras nombradas confirmado (`"Stress correct on 1/3 word(s) — check: average, village."`), y `curl -I /app.js` confirma el header `cache-control: no-cache` presente.

Suite completa: 191/191 (3 de integración deseleccionados).

---

### Fase 9.13 — Sílaba tónica en mayúsculas + respelling fonético simple ✅

El usuario preguntó qué significa "stress correct" y cómo mostrar el acento tónico en la app; pidió 2 cosas concretas: (1) la palabra con la sílaba tónica en mayúsculas (ej. "aVERage"), y (2) junto al IPA (rule_ipa, "esa con los símbolos y letras raras"), una guía de pronunciación simple sin símbolos raros (ej. "book" → "buk").

**Investigado y descartado:** `pyphen` (hyphenation) para derivar sílabas de la ortografía automáticamente — probado a mano contra el corpus real: falla en palabras cortas/comunes ("about" no separa nada, "banana" da solo 2 partes en vez de 3) porque las librerías de hyphenation optimizan puntos de corte de línea, no límites silábicos lingüísticos.

**Diseño de 2 piezas, con la misma filosofía que el markup `~x~`/`*x*` de Fase 9.7 (curar a mano lo que no es confiable derivar automáticamente):**

1. **`family_stress`** (curado a mano, `corpus/patterns.csv`, columna nueva paralela a `family`): capitalización ortográfica de la sílaba tónica para las 25 palabras de patrón (ej. `"AVerage"`, `"aBOUT"`). Palabras de una sola sílaba (kn-/wr-) quedan sin mayúsculas — no hay contraste de acento que marcar. Requirió migración manual (`_migrate()` en `database.py`, `ALTER TABLE ... ADD COLUMN` si falta) porque `CREATE TABLE IF NOT EXISTS` no agrega columnas a una tabla ya creada por una versión anterior del schema (la DB real del volumen Docker).

2. **`simple_respelling(word)`** (`backend/services/phoneme.py`, general y automático, sin curar a mano): guía de pronunciación con letras comunes en vez de IPA — ej. `simple_respelling("book") == "buk"`. Basado en fonemas de CMU dict (no en ortografía, para no repetir el problema de pyphen): `_syllabify_phonemes()` agrupa fonemas por "maximal onset" (cada consonante entre 2 vocales va con la sílaba SIGUIENTE), `_ARPABET_TO_RESPELL` mapea cada fonema a letras simples, la sílaba con acento primario (`...1`) se pone en mayúsculas si hay más de una sílaba. `curriculum.py` calcula `family_respelling` al vuelo llamando `simple_respelling()` sobre cada palabra de `family` (sin el markup `~`/`*`) — no se guarda en la DB, a diferencia de `family_stress`.

Tests nuevos: `tests/services/test_respelling.py` (5 casos, incluye "average"→"A-ver-ij", "about"→"uh-BOWT", "banana"→"buh-NA-nuh"), `test_pattern_of_the_day_includes_stress_caps_and_respelling`, `test_pattern_family_stress_matches_family_length`, `test_reseeding_updates_pattern_family_stress`, `test_app_js_renders_pattern_family_stress_and_respelling`.

`renderPatternFamily()` en `app.js` ahora recibe `family`, `familyStress`, `familyRespelling` (paralelos) y muestra, junto a cada palabra: `aver<mark>age</mark> (AVerage · A-ver-ij)`.

**Verificado en vivo (Chrome, DB real re-seedeada):** `/api/today` devuelve `family_stress`/`family_respelling` correctos para los 5 patrones; capturado en pantalla el patrón "-age/-idge" mostrando `average (AVerage · A-ver-ij)`, `village (VILlage · VIL-ij)`, etc. con el highlight `<mark>` de Fase 9.7 intacto.

Suite completa: 200/200 (3 de integración deseleccionados).

---

### Fase 9.14 — Control de velocidad de reproducción en módulo 1 ✅

El usuario reportó que módulo 1 reproduce las palabras "super rápido" y pidió elegir velocidad: lento, normal, rápido.

**Fix:** 3 botones (`#speed-slow-btn`/`#speed-normal-btn`/`#speed-fast-btn`) sobre "Listen to examples" en `index.html`. `SPEED_VALUES = { slow: 0.7, normal: 1, fast: 1.3 }` en `app.js` (valores típicos de apps de pronunciación, no vienen de una API — Kokoro/OpenAI TTS no tienen parámetro de velocidad en su síntesis, así que se controla client-side con `audio.playbackRate`, no regenerando el audio). `playText()`/`playTextWithButton()` reciben un `rate` opcional; `listenPatternBtn` lo pasa desde la variable global `playbackSpeed`, que los 3 botones actualizan y reflejan visualmente con la clase `speed-active`. Solo módulo 1 — el botón "Listen" de módulo 2 (chunk) queda sin cambios, no fue parte del pedido.

Tests nuevos: `test_index_html_has_speed_control_buttons_in_module_1`, `test_app_js_speed_buttons_set_playback_rate`, `test_app_js_speed_selection_applies_to_pattern_listen_button`.

**Verificado en vivo (Chrome):** click en "Slow" cambia `playbackSpeed` a `0.7` y activa la clase visual correcta (confirmado inspeccionando el estado real de la página, no solo el código); clic en "Listen to examples" dispara `POST /api/speak` con 200 OK (confirmado por network log). No se pudo confirmar el audio real audible en este entorno de automatización de Chrome — `audio.play()` no resuelve su promesa en esta sesión (limitación conocida de reproducir audio vía CDP sin salida de audio real / activación de usuario reconocida, no es un bug del código: `audio.playbackRate` se asigna antes de `await audio.play()`, y el mismo patrón de `playTextWithButton` ya se usaba antes de este cambio para los botones "Listen").

Suite completa: 203/203 (3 de integración deseleccionados).

---

### Fase 9.15 — Un patrón se quedaba atascado para siempre (bug real de rotación) ✅

El usuario reportó: "cada vez que uso la app, me salen solo los mismos ejercicios".

**Causa raíz:** `_pattern_of_the_day()` (`curriculum.py`) elige el patrón con `accuracy` más baja (`ORDER BY accuracy ASC`). El patrón "letras mudas kn-/wr-" tiene las 5 palabras de su familia monosílabas (know, knee, write, wrong, knife) — y `analyze_stress()` ignora explícitamente las monosílabas (no hay contraste de sílaba tónica que medir), así que `stress_results` quedaba SIEMPRE vacío para ese patrón, sin importar qué tan bien se pronunciara. `log_pattern_practiced()` solo actualiza `accuracy` cuando recibe `stress_results` — sin eso, llamaba a `upsert_pattern_progress()` sin `correct`/`total`, y la `accuracy` se quedaba congelada en `0.0` para siempre (confirmado en la DB real: 16 sesiones practicadas, `accuracy = 0.0` exacto). Con el mínimo posible siempre en 0.0, ese patrón dominaba la selección de "menos practicado" indefinidamente — nunca podía mejorar ni rotar.

**Fix:** nueva función `count_words_evaluated()` (`phoneme.py`) — cuenta cuántas target_words aparecen en la transcripción y son evaluables por `analyze_phonemes()` (están en CMU dict), sin importar el número de sílabas (a diferencia de `analyze_stress`). Se expone como `phoneme_evaluated` en `Transcript`/`/api/transcribe`. `log_pattern_practiced()` ahora tiene un fallback: si no hay `stress_results` pero sí `phoneme_evaluated`, calcula `correct = phoneme_evaluated - len(phoneme_errors)` y actualiza `accuracy` real con eso — mismo mecanismo de spaced-repetition que ya tenían los otros 4 patrones, ahora también disponible para el único 100% monosílabo. Sin ninguna señal (ni stress_results ni phoneme_evaluated — ej. el alumno no dijo nada reconocible), el comportamiento previo se mantiene (no se inventa un accuracy).

Se reseteó a mano la fila de `pattern_progress` del patrón afectado en la DB real (los 16 registros previos eran datos inválidos, calculados con la fórmula rota — un accuracy promedio pesado por 16 "no-señal" contados como 0% habría seguido dominando la selección aun con el código arreglado).

Tests nuevos: `test_count_words_evaluated_*` (`test_phoneme.py`), `test_transcribe_and_analyze_computes_phoneme_evaluated_count` (`test_acoustic.py`), `test_log_pattern_practiced_updates_accuracy_from_phoneme_evaluated_when_no_stress_results` + `test_log_pattern_practiced_keeps_accuracy_frozen_without_any_signal` (`test_log.py`), `test_log_pattern_practiced_uses_phoneme_evaluated_when_no_stress_results` (`test_session.py`), `test_app_js_pattern_recording_sends_phoneme_evaluated` (`test_session_modules.py`).

**Verificado en vivo:** ciclo completo TTS→transcribe→log contra el patrón real "letras mudas kn-/wr-" (`/api/speak` con las 5 palabras → `/api/transcribe` con `target_words` → `/api/log`), confirmado que `phoneme_evaluated` llega no-cero y `pattern_progress.accuracy` deja de estar congelado en exactamente `0.0`.

**Nota de diseño, no bug:** el algoritmo prioriza intencionalmente el patrón con peor accuracy ("practica lo que menos dominas primero") — con el fix, ese patrón ya puede mejorar y rotar con la práctica real, pero seguirá apareciendo seguido mientras siga siendo el más débil. Eso es la hipótesis de ITER-2, no un bug.

Suite completa: 211/211 (3 de integración deseleccionados).

---

### Fase 9.16 — Módulo 2 y módulo 3 también repetían siempre lo mismo (motor de repaso espaciado nunca escrito) ✅

El usuario reportó: "módulo 2 sigue repitiendo el chunk 'be careful with that', seguro pasa lo mismo en módulo 3" — confirmado, y peor de lo esperado en un caso.

**Causa raíz (3 mecanismos distintos, mismo patrón: la lectura del motor de repaso espaciado estaba construida, la escritura nunca):**

1. **Módulo 2 (chunk repetido):** `_chunk_of_the_day()` ordena por `chunk_spontaneous` (uso espontáneo en conversación libre, DESIGN.md) — pero esa columna nunca se escribía en ningún lado del código (la detección de uso espontáneo en módulo 3 no existía). Siempre 0 para todos los chunks, el desempate caía en el rango de la palabra (que nunca cambia), y "be" (rank más bajo) siempre ganaba.
2. **Módulo 3 (week_words repetidas):** peor — `user_progress` (de donde salen las `week_words`) tenía **0 filas, siempre**, porque ningún código escribía ahí. Las 5 palabras de la semana no repetían seguido: nunca cambiaban en absoluto, en ninguna sesión.
3. **Bonus, mismo patrón:** `sessions.comprehensibility` tampoco se escribía nunca, así que `_difficulty()` estaba permanentemente clavada en `"maintain"`.

**Fix (3 piezas, alcance acordado con el usuario — "los tres ahora"):**

1. **Módulo 2:** `_chunk_of_the_day()` ahora también cuenta `produced_uses` (`chunk_produced`, que SÍ se registra desde siempre vía `mark_chunk_used` en la práctica forzada de módulo 2) como segundo criterio de desempate, antes de caer al rango de la palabra. Rotación real desde el día 1, sin esperar a que exista uso espontáneo.
2. **Detección de uso espontáneo real (para que `chunk_spontaneous` deje de estar muerto):** `mark_chunk_spontaneous()` (`database.py`) + `log_chunk_spontaneous_use()` (`log.py`, mismo criterio de matching que `log_chunk_used` pero en columna separada — no pisa el resultado de módulo 2) + nuevo evento `/api/log` `event=chunk_spontaneous`. Módulo 3 lo manda después de cada turno si hay `chunk_today`.
3. **Repaso espaciado real para week_words:** `services/spaced_rep.py` (nuevo — DESIGN.md ya lo nombraba, nunca se había creado), variante simplificada de SM-2 sin ease factor (no hay calificación de calidad 0-5, solo señal binaria "la palabra apareció"): intervalos fijos crecientes (1/3/7/14/30 días) y score que sube +0.15 por uso exitoso, tope 1.0. `upsert_user_progress()` (`database.py`) + `log_words_used()` (`log.py`, matching por tokens contra la transcripción) + nuevo evento `/api/log` `event=words_used`. **Solo evidencia positiva** — no usar una palabra en una charla en particular NO la penaliza (el alumno puede simplemente no haber tenido ocasión), mismo criterio que `pattern_progress`/`phoneme_evaluated` de Fase 9.15. `_forms_to_review()` ahora expone `form_id` (necesario para que el frontend pueda mandarlo de vuelta).
4. **Comprehensibility:** DESIGN.md proponía que el LLM tutor la evalúe en cada turno — se decidió NO hacerlo así (una llamada/salida estructurada extra por turno solo para un número, costo y latencia adicionales, más riesgo de romper el prompt conversacional ya afinado). En su lugar, `services/comprehension.py` (nuevo) deriva un proxy determinístico de wpm + proporción de fillers (ya calculados por turno, sin costo extra) — documentado explícitamente como desviación de diseño respecto a DESIGN.md. `create_session`/`update_session` (`database.py`) ahora aceptan y persisten `comprehensibility`; `get_tutor_reply` (`tutor.py`) la calcula y la pasa. Sin evidencia (transcripción vacía), devuelve `None` en vez de inventar un valor.

Tests nuevos: `test_chunk_of_the_day_prefers_least_produced_uses` (`test_curriculum.py`), `test_mark_chunk_spontaneous_updates_session_row` + `test_upsert_user_progress_*` + `test_create/update_session_persists_comprehensibility` (`test_database.py`), `test_next_review_date_*` + `test_score_after_success_*` (`test_spaced_rep.py`, nuevo), `test_estimate_comprehensibility_*` (`test_comprehension.py`, nuevo), `test_log_chunk_spontaneous_*` + `test_log_words_used_*` (`test_log.py`), `test_log_chunk_spontaneous_marks_session_when_chunk_appears` + `test_log_words_used_updates_user_progress` (`test_session.py`), `test_tutor_persists_comprehensibility_estimate` + `test_tutor_leaves_comprehensibility_null_for_empty_text` (`test_tutor.py`), `test_app_js_free_conversation_logs_chunk_spontaneous_use` + `test_app_js_free_conversation_logs_words_used` (`test_session_modules.py`).

**Verificado en vivo, ciclo completo real:** TTS con el chunk del día + una week_word → `/api/transcribe` → `/api/tutor` → `/api/log` (`chunk_spontaneous` y `words_used`) — confirmado en la DB real: `sessions.comprehensibility = 3.07` (antes siempre `NULL`), `sessions.chunk_spontaneous = 1`, `user_progress` con 2 filas nuevas (antes 0, siempre). `/api/today` confirmado sirviendo un chunk distinto y `week_words` distintas después de la práctica — la rotación funciona de punta a punta.

Suite completa: 237/237 (3 de integración deseleccionados).

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
docker compose up -d --force-recreate speakwise   # aplicar cambios en .env (restart NO alcanza)
docker compose exec speakwise python -m pytest -v            # correr toda la suite (integration excluidos por default)
docker compose exec speakwise python -m pytest -v -k seed     # correr un subset
docker compose exec speakwise python -m pytest -v -m integration   # tests de integración real (gasta API)
docker compose logs -f                              # logs en vivo
```

---

## Historial

| Versión | Fecha | Cambio |
|---|---|---|
| 1.0 | Ago 2026 | Plan inicial, cubre ITER-1 completa del BACKLOG con TDD y consolidación a GitHub |
