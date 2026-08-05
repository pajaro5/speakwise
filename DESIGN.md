# DESIGN — Arquitectura Técnica · SpeakWise

Fuente de verdad para: estructura de archivos, schema de DB, contratos de API.
**No contiene:** código de implementación ni algoritmos. Eso es trabajo del agente.

---

## 1. Visión general

```
┌─────────────────────────────────────────────────────────┐
│                     RED WiFi LOCAL                      │
│   PC (servidor)              MÓVIL (cliente)            │
│   FastAPI :8000    ◄────►    Browser / PWA              │
│   Whisper API (STT)          Web Audio API              │
│   OpenAI TTS                 http://192.168.X.X:8000    │
│   Claude API (LLM)           Instalable como PWA        │
│   SQLite (DB)                                           │
└─────────────────────────────────────────────────────────┘
```

---

## 2. Stack

> **Principio de selección de providers (desde Fase 3 de `planVersion1.md`):** 1) software libre / local primero, siempre que el hardware lo soporte, 2) si hace falta un servicio pago, usar la alternativa más económica disponible. Cada provider tiene su interfaz común en `providers/base.py`, se elige por variable de entorno vía `providers/factory.py`.
>
> **Excepción — LLM:** Ollama+Qwen (7B local) quedó implementado y testeado (`providers/llm_ollama.py`) pero **no es el default**: la PC de desarrollo no tiene recursos para correr un modelo de 7B parámetros de forma razonable. El default de LLM es **DeepSeek** (paga, la más económica frente a Claude/GPT). Ollama sigue disponible por `LLM_PROVIDER=ollama_qwen` para cuando se use en una máquina con más recursos.

| Capa | Default | Alternativa | Licencia (default) |
|---|---|---|---|
| STT | `faster-whisper` local (`whisperx_local`) — libre, liviano | Whisper API (`whisper_api`) | MIT |
| Fonemas | *(no en MVP)* | — | — |
| Acústico | librosa (WPM) | — | ISC / GPL |
| TTS | Kokoro-82M local (`kokoro`) — libre, liviano | OpenAI TTS (`openai`) | Apache 2.0 |
| LLM | **DeepSeek** (`deepseek`) — paga, la más económica | Ollama+Qwen (`ollama_qwen`, libre pero pesado — 7B) → Claude API (`claude`) | — |
| Backend | FastAPI | — | MIT |
| Frontend | HTML/JS + PWA | — | — |
| DB | SQLite | — | Dominio público |
| Corpus ref. | CMU Pronouncing Dict | — | Libre |

---

## 3. Estructura de archivos

```
speakwise/
├── pyproject.toml
├── .env.example
│
├── backend/
│   ├── main.py               ← app FastAPI, montar routers, servir frontend
│   ├── database.py           ← conexión SQLite, context manager, queries
│   ├── config.py             ← leer .env, validar variables obligatorias
│   ├── seed.py               ← poblar corpus desde CSV
│   │
│   ├── routers/
│   │   ├── session.py        ← /transcribe /tutor /speak /worksheet
│   │   └── progress.py       ← /today /panel /progress /stats
│   │
│   ├── services/
│   │   ├── curriculum.py     ← Curriculum Engine
│   │   ├── acoustic.py       ← pipeline STT + análisis
│   │   ├── tutor.py          ← system prompt + LLM + persistencia de sesión
│   │   ├── log.py            ← POST /api/log: tracking de patrón/chunk (Fase 9)
│   │   ├── patterns.py       ← detección de patrones fonéticos
│   │   ├── spaced_rep.py     ← algoritmo SM-2
│   │   ├── worksheet.py      ← generación de hoja de trabajo
│   │   └── exceptions.py     ← excepciones de dominio
│   │
│   └── providers/
│       ├── base.py           ← interfaces abstractas STT / TTS / LLM
│       ├── factory.py        ← selección de provider por variable de entorno
│       ├── stt_whisper_api.py
│       ├── stt_whisperx.py
│       ├── tts_openai.py
│       ├── tts_kokoro.py
│       ├── llm_claude.py
│       └── llm_ollama.py
│
├── frontend/
│   ├── index.html
│   ├── app.js
│   ├── styles.css
│   ├── manifest.json
│   └── service-worker.js
│
├── templates/
│   └── worksheet.html        ← Jinja2, @media print
│
└── corpus/
    ├── words.csv             ← lemmas + formas + traducción ES (fonemas se derivan de cmudict en seed.py, no se guardan en CSV)
    └── patterns.csv          ← patrones fonéticos + familias
```

> **Nota de implementación (Fase 2 de `planVersion1.md`):** no existe `chunks.csv`. Los chunks del ITER-1 se generan en `seed.py` a partir de plantillas por tense (`CHUNK_TEMPLATES`) aplicadas a `words.csv`, para no duplicar el mismo dato en dos archivos. Curación manual de chunks más ricos queda para una iteración futura. Los fonemas ARPAbet tampoco se hand-authoring: `seed.py` los deriva de `cmudict` (ya dependencia del proyecto) por forma, incluyendo `lfc_focus`/`stress_syl` calculados como la vocal con estrés primario (`...1`).

---

## 4. Base de datos — Schema completo

### Corpus (estático — seed.py lo carga una vez)

```sql
CREATE TABLE words (
    id       INTEGER PRIMARY KEY,
    lemma    TEXT NOT NULL,
    rank     INTEGER,
    type     TEXT    -- "irregular_verb"|"regular_verb"|"noun"|"adj"|"adv"
);

CREATE TABLE word_forms (
    id         INTEGER PRIMARY KEY,
    word_id    INTEGER REFERENCES words(id),
    form       TEXT NOT NULL,
    tense      TEXT,     -- "base"|"past"|"progressive"|"third_sg"|"past_participle"
    phonemes   TEXT,     -- ARPAbet separado por espacios: "T AO1 T"
    lfc_focus  TEXT,     -- fonema LFC prioritario: "AO1"
    stress_syl INTEGER   -- índice de sílaba tónica (0 = primera)
);

CREATE TABLE word_properties (
    word_id        INTEGER REFERENCES words(id),
    translation_es TEXT,
    register       TEXT,  -- "formal"|"informal"|"neutral"
    topic_tags     TEXT   -- JSON array: ["trabajo","social"]
);

CREATE TABLE chunks (
    id       INTEGER PRIMARY KEY,
    word_id  INTEGER REFERENCES words(id),
    chunk    TEXT NOT NULL,
    tense    TEXT,
    function TEXT,
    level    INTEGER DEFAULT 1  -- 1=básico 2=intermedio 3=avanzado
);

CREATE TABLE phonetic_patterns (
    id       INTEGER PRIMARY KEY,
    name     TEXT,      -- "-age/-idge"
    rule_es  TEXT,      -- "Termina en -age = /ɪdʒ/, la E no suena"
    rule_ipa TEXT,
    family   TEXT,      -- JSON array: ["average","manage","village"]
    priority INTEGER    -- 1=alta para hispanohablantes
);

CREATE TABLE curriculum_plan (
    week          INTEGER,
    word_id       INTEGER REFERENCES words(id),
    phoneme_focus TEXT
);
```

### Progreso (dinámico — crece con cada sesión)

```sql
CREATE TABLE sessions (
    id                INTEGER PRIMARY KEY,
    date              TEXT,
    duration_sec      INTEGER,
    topic             TEXT,
    transcript        TEXT,
    wpm               REAL,
    fillers           INTEGER,
    comprehensibility REAL,       -- 1.0-5.0, Claude evalúa
    chunk_used        TEXT,
    chunk_produced    INTEGER,    -- 1/0
    chunk_spontaneous INTEGER,    -- 1/0
    stress_correct    REAL,       -- % turnos con stress correcto
    phoneme_errors    TEXT,       -- JSON: [{word, expected, produced}]
    pattern_focus     TEXT,
    feedback          TEXT,
    prompts_shown     INTEGER DEFAULT 0,
    prompts_used      INTEGER DEFAULT 0,
    prompt_ratio      REAL,
    panel_mode        TEXT,       -- "full"|"tap_to_show"|"minimal"
    worksheet_path    TEXT
);

CREATE TABLE user_progress (
    id          INTEGER PRIMARY KEY,
    form_id     INTEGER REFERENCES word_forms(id),
    context     TEXT NOT NULL,
    -- "input"|"phonetic"|"chunk_receptive"|"chunk_productive"
    -- |"conv_receptive"|"conv_productive"|"fluency"
    exposures   INTEGER DEFAULT 0,
    last_seen   TEXT,
    score       REAL DEFAULT 0.0,
    next_review TEXT
);

CREATE TABLE pattern_progress (
    id                 INTEGER PRIMARY KEY,
    pattern_id         INTEGER REFERENCES phonetic_patterns(id),
    stage              INTEGER DEFAULT 1,  -- 1=audición 2=reconoc. 3=producción 4=auto
    accuracy           REAL DEFAULT 0.0,
    sessions_practiced INTEGER DEFAULT 0,
    last_seen          TEXT,
    next_review        TEXT
);

CREATE TABLE phoneme_log (
    id          INTEGER PRIMARY KEY,
    session_id  INTEGER REFERENCES sessions(id),
    word        TEXT,
    phoneme_exp TEXT,
    phoneme_got TEXT,
    correct     INTEGER  -- 1/0
);

CREATE INDEX idx_progress_form    ON user_progress(form_id);
CREATE INDEX idx_progress_context ON user_progress(context, score);
CREATE INDEX idx_sessions_date    ON sessions(date);
CREATE INDEX idx_phoneme_word     ON phoneme_log(word);
CREATE INDEX idx_pattern_stage    ON pattern_progress(stage, accuracy);
```

---

## 5. API — Endpoints y contratos

| Método | Endpoint | Descripción |
|---|---|---|
| `POST` | `/api/transcribe` | Audio → texto + métricas |
| `POST` | `/api/tutor` | Transcripción + historial → respuesta Claude |
| `POST` | `/api/speak` | Texto → audio TTS stream |
| `POST` | `/api/session/start` | Crea la fila de `sessions`, devuelve `session_id` (agregado Fase 9) |
| `GET` | `/api/today` | Plan pedagógico del día (≤ 300 tokens de corpus) |
| `GET` | `/api/panel` | Panel de apoyo para conversación libre |
| `POST` | `/api/log` | Registrar exposición al finalizar turno |
| `POST` | `/api/worksheet/{session_id}` | Generar hoja de trabajo HTML |
| `GET` | `/api/progress` | Dashboard: métricas de las últimas 30 sesiones |

### POST /api/transcribe

```json
// Request: multipart/form-data  { "audio": file.webm }

// Response (MVP)
{
  "text": "I was thinking maybe we could average the results",
  "wpm": 94.3,
  "fillers": 0,
  "words": [{"w": "average", "start": 2.1, "end": 2.8}]
}

// Response (V2 — agrega análisis acústico)
{
  "text": "...",
  "wpm": 94.3,
  "fillers": 0,
  "words": [...],
  "stress_results": [{"word": "average", "expected_syl": 0, "detected_syl": 1, "correct": false}],
  "phoneme_errors": [{"word": "average", "expected": "AE1", "produced": "AH1"}],
  "pattern_errors": {"-age/-idge": 1}
}
```

### POST /api/tutor

*(Contrato definido en Fase 6 de `planVersion1.md` — no estaba especificado con ejemplo.)*

```json
// Request
{
  "text": "I go to work yesterday",
  "history": [{"role": "user", "content": "..."}, {"role": "assistant", "content": "..."}],
  "session_id": null,
  "topic": "tu semana de trabajo",
  "wpm": 85.5,
  "fillers": 1
}

// Response
{
  "reply": "Try 'I went to work yesterday' instead — 'go' becomes 'went' in the past.",
  "session_id": 42
}
```

`session_id: null` crea una sesión nueva; pasar el `session_id` devuelto actualiza esa misma fila en `sessions` en vez de crear una nueva. `wpm`/`fillers` vienen del response de `/api/transcribe` del mismo turno.

### POST /api/speak

```json
// Request
{"text": "Great job!", "voice": "default"}

// Response: audio/mpeg (bytes), no JSON
```

### POST /api/session/start

*(Agregado en Fase 9 de `planVersion1.md` — necesario para que los 3 módulos de una sesión compartan `session_id` desde el principio, en vez de crearlo recién en el primer `/api/tutor`.)*

```json
// Request
{"topic": "tu semana de trabajo"}

// Response
{"session_id": 42}
```

Llamar esto al empezar la sesión, y pasar el `session_id` devuelto a `/api/tutor` y `/api/log` durante toda la sesión (en vez de dejar que `/api/tutor` cree uno nuevo).

### POST /api/log

*(Contrato definido en Fase 9 — antes solo estaba el nombre del endpoint en la tabla.)*

```json
// Request — practicar un patrón fonético (módulo nuclear stress)
{"session_id": 42, "event": "pattern_practiced", "pattern_id": 3}
// Response
{"ok": true}

// Request — registrar uso del chunk del día (módulo chunk)
{"session_id": 42, "event": "chunk_used", "chunk": "I was thinking maybe", "transcript": "well I was thinking maybe we go"}
// Response
{"ok": true, "produced": true}
```

`pattern_practiced` solo cuenta exposición (`pattern_progress.sessions_practiced`) — no hay scoring de precisión todavía, eso requiere el análisis de fonemas de ITER-2 que no existe. `chunk_used` verifica por substring (case-insensitive) si el chunk aparece en la transcripción.

### POST /api/chunk-examples

Pedido por el usuario probando módulo 2 ("quiero que muestre 3 ejemplos de uso"). No es contenido curado — se genera con el LLM configurado (`services/chunk_examples.py`), porque curar a mano 3 ejemplos × 200 chunks no escala. El frontend lo llama automáticamente al entrar a módulo 2 (no bloquea el resto del módulo, que ya tiene el chunk/función desde `/api/today`).

```json
// Request
{"chunk": "Be careful with that.", "function": "imperative"}
// Response
{
  "sentence": "Be careful with that.",
  "paragraph": "I know this road is tricky. Be careful with that curve ahead. Slow down before you get there.",
  "conversation": "A: I'm going to fix the wiring myself.\nB: Be careful with that — turn off the power first."
}
```

Si el LLM no devuelve JSON válido o falta algún campo, `ProviderUnavailableError` → 503 (mismo patrón que `/api/tutor`).

### GET /api/today

```json
// Response — siempre ≤ 300 tokens de corpus
{
  "week_words": [
    {"form": "thought", "tense": "past", "lfc_focus": "AO1", "score": 0.41}
  ],
  "pattern_focus": {
    "id": 3,
    "name": "-age/-idge",
    "rule_es": "Termina en -age = /ɪdʒ/, la E no suena",
    "rule_ipa": "/ɪdʒ/",
    "family": ["average", "manage", "village"]
  },
  "chunk_today": {
    "chunk": "I was thinking maybe...",
    "function": "tentative_proposal",
    "spontaneous_uses": 0
  },
  "difficulty": "maintain",
  "topic_options": ["tu semana de trabajo", "un viaje planeado", "algo que viste"],
  "conversation_starters": ["So, how's it going?", "What have you been up to lately?", "So, tell me about your day."],
  "linking_words": ["for example", "however", "between"]
}
```

`conversation_starters` y `linking_words` son pools curados en código (`curriculum.py`, sin tabla propia — igual que `topic_options`), 3 al azar por request. Apoyo para conversación libre pedido por el usuario tras probar la sesión real ("me quedo en blanco"): 3 categorías — frases para iniciar la charla, conectores para enlazar ideas, y temas (`topic_options`, ya existente).

---

## 6. Pipeline acústico — flujo por fase

**MVP (Whisper API):**
```
Audio → Whisper API → { text, word_timestamps }
      → calcular WPM y fillers desde timestamps
```

**V2 (WhisperX + Parselmouth):**
```
Audio → WhisperX → { text, word_timestamps, phoneme_timestamps }
      → CMU Dict  → fonemas esperados por palabra
      → diff      → phoneme_errors[]
      → librosa + Parselmouth → energy/pitch por palabra
      → comparar con CMU stress marker → stress_results[]
      → agrupar errores por patrón → pattern_errors{}
```

---

## 7. Curriculum Engine — qué hace GET /api/today

Ejecuta 3 queries SQL y devuelve el contexto del día. Total ≤ 300 tokens.

| Query | Qué selecciona |
|---|---|
| Formas a revisar | `user_progress` WHERE `next_review <= today` AND `context = conv_prod`, ORDER BY `score ASC`, LIMIT 5 |
| Patrón del día | `pattern_progress` WHERE `stage < 4`, ORDER BY `accuracy ASC`, LIMIT 1 |
| Chunk del día | `chunks` del top-150 palabras con menor `chunk_spontaneous` acumulado |
| Dificultad | `AVG(comprehensibility)` últimas 5 sesiones: > 4.0 → "increase", < 3.0 → "decrease" |

---

## 8. Panel de apoyo — modos

| Semanas | Modo | Criterio de avance |
|---|---|---|
| 1-3 | `full` — siempre visible | — |
| 4-6 | `tap_to_show` — al tocar | `prompt_ratio < 0.5` por 5 sesiones |
| 7-9 | `minimal` — 3 palabras + resto al tocar | `prompt_ratio < 0.3` por 5 sesiones |
| 10+ | Solo fillers | `prompt_ratio < 0.15` por 5 sesiones |

`autonomy = 1 - AVG(prompt_ratio)` — métrica visible en el dashboard.

---

## 9. Variables de entorno

```bash
# STT/TTS: default libre y local (livianos). LLM: default DeepSeek (paga, la mas
# barata) -- Ollama+Qwen es libre pero pesa 7B, no es el default (ver §2).
STT_PROVIDER=whisperx_local    # whisperx_local (default) | whisper_api
TTS_PROVIDER=kokoro            # kokoro (default) | openai
LLM_PROVIDER=deepseek          # deepseek (default) | ollama_qwen | claude

ANTHROPIC_API_KEY=
OPENAI_API_KEY=
DEEPSEEK_API_KEY=

HOST=0.0.0.0
PORT=8000
DB_PATH=/app/data/speakwise.db

# STT local (default)
WHISPER_MODEL=base

# Ollama: no se usa por default (ver nota arriba), pero el provider/config
# quedan listos para cuando se corra en una maquina con mas recursos.
OLLAMA_MODEL=qwen2.5:7b
OLLAMA_URL=http://ollama:11434

API_COST_ALERT_USD=30
```

---

## 10. Interfaces de providers — el contrato

```python
@dataclass
class Transcript:
    text: str
    wpm: float
    words: list[dict]      # [{w, start, end}]
    phonemes: list[dict]   # [{p, start, end}] — vacío en MVP
    fillers: int

class STTProvider(ABC):
    @abstractmethod
    async def transcribe(self, audio: bytes) -> Transcript: ...

class TTSProvider(ABC):
    @abstractmethod
    async def synthesize(self, text: str, voice: str = "default") -> bytes: ...

class LLMProvider(ABC):
    @abstractmethod
    async def complete(self, messages: list, system: str, max_tokens: int = 400) -> str: ...
```

> **Nota de implementación:** el `STTProvider.transcribe()` concreto (`stt_whisper_api.py`) devuelve texto y timestamps crudos de la API de Whisper. El cálculo de `wpm` y `fillers` a partir de esos timestamps lo hace `services/acoustic.py`, que arma el `Transcript` final antes de devolverlo al router — no el provider. Esto respeta la regla de `CODING_STANDARDS.md` §2 de que `providers` nunca importa `services`.

---

## Historial

| Versión | Fecha | Cambio |
|---|---|---|
| 1.0 | Jul 2025 | Documento inicial |
| 1.1 | Jul 2025 | Recorte post-auditoría: eliminado código de implementación, corregidos DB_PATH, OLLAMA_URL, pipeline MVP vs V2, añadidos config.py y exceptions.py al árbol |
| 1.2 | Ago 2026 | Fase 1 de planVersion1.md: agregado `providers/factory.py` al árbol, aclarado que `wpm`/`fillers` los calcula `acoustic.py`, no el provider |
| 1.3 | Ago 2026 | Fase 2 de planVersion1.md: eliminado `chunks.csv` del árbol (se generan en `seed.py`), aclarado que fonemas ARPAbet se derivan de `cmudict`, no se hand-authoring en CSV |
| 1.4 | Ago 2026 | Fase 3 de planVersion1.md: providers locales/libres (`whisperx_local`, `kokoro`, `ollama_qwen`) pasan a ser el default en MVP, no V2 — decisión explícita del usuario ("todo en lo posible sea con software libre"). Agregado `llm_deepseek.py` como alternativa paga más económica que Claude cuando se necesite un servicio contratado. |
| 1.5 | Ago 2026 | Ollama+Qwen removido de `docker-compose.yml` y como default de LLM — la PC de desarrollo no soporta correr un modelo de 7B. Nuevo default de LLM: DeepSeek (paga, más económica). El provider `llm_ollama.py` queda en el código, disponible por env var para uso futuro en otra máquina. |
| 1.6 | Ago 2026 | Fase 6 de planVersion1.md: agregados contratos de `POST /api/tutor` y `POST /api/speak` (no estaban especificados con ejemplo). `session_id` en `/tutor` decide crear vs actualizar la fila de `sessions`. |
| 1.7 | Ago 2026 | Fase 9 de planVersion1.md (parte 1, backend): agregado `POST /api/session/start` (no estaba en el árbol original de endpoints) y definido el contrato de `POST /api/log` (antes solo el nombre). Agregado `services/log.py` y `services/tutor.py` al árbol de archivos. |
