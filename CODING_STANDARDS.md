# CODING STANDARDS — SpeakWise

Reglas que el agente debe seguir. No contiene ejemplos de implementación.

---

## 1. Principios

| Principio | Regla concreta |
|---|---|
| Explícito sobre implícito | Type hints en todas las funciones. Nombres descriptivos. |
| Una responsabilidad | Routers: solo HTTP. Servicios: solo lógica. Providers: solo adaptadores externos. |
| Fallar en voz alta | Nunca silenciar excepciones (`except: pass` está prohibido). |
| Sin hardcoding | Toda configuración desde `config.py` que lee `.env`. |
| Async es la norma | Toda IO es async. Código CPU-bound (librosa, Parselmouth) corre en `ThreadPoolExecutor`. |

---

## 2. Estructura de módulos y reglas de dependencia

```
backend/
├── main.py           ← crea app, monta routers, sirve frontend
├── database.py       ← conexión SQLite, get_db(), helpers de query
├── config.py         ← lee .env, valida variables obligatorias
├── seed.py           ← carga corpus desde CSV
├── routers/          ← capa HTTP únicamente
├── services/         ← lógica de negocio
│   └── exceptions.py ← excepciones de dominio propias
└── providers/        ← adaptadores de servicios externos
    └── base.py       ← interfaces abstractas (el contrato)
```

**Dirección de dependencias permitida:**
```
routers → services → providers → APIs externas
routers → database (excepcional, solo lectura)
services → database
```

**Prohibido:**
- `services` importa `FastAPI` o `HTTPException`
- `providers` importa `database` o `services`
- Lógica de negocio en `routers`

---

## 3. Naming

| Elemento | Convención | Ejemplo |
|---|---|---|
| Módulos y archivos | `snake_case` | `spaced_rep.py`, `stt_whisper_api.py` |
| Clases | `PascalCase` | `CurriculumEngine`, `WhisperAPIProvider` |
| Funciones y variables | `snake_case` | `build_todays_plan()`, `wpm_avg` |
| Constantes de módulo | `UPPER_SNAKE_CASE` | `DEFAULT_WHISPER_MODEL = "base"` |
| Endpoints | `kebab-case` | `/api/today-plan`, `/api/transcribe` |

---

## 4. Type hints

Obligatorios en todas las funciones. Sin excepciones.

Usar `@dataclass` para estructuras internas. Usar `pydantic.BaseModel` para request/response de FastAPI.

---

## 5. Routers

- Máximo 5 líneas por handler
- Reciben request → llaman servicio → devuelven response
- Sin lógica de negocio
- Los servicios se inyectan como dependencias FastAPI (`Depends(get_service)`) o se importan como módulos
- Status codes: `200` éxito con datos, `201` recurso creado, `204` sin contenido, `422` input inválido, `503` servicio externo caído

---

## 6. Base de datos

- `get_db()` es una **función generadora** (con `yield`) registrada como dependencia FastAPI — no usa `@contextmanager`
- `database.py` también expone un context manager separado (`db_connection()`) para uso en `seed.py` y tests
- SQL siempre con parámetros (`?` o `:nombre`) — nunca f-strings ni concatenación
- Una función por query en `database.py` — los servicios llaman funciones, no escriben SQL directamente
- `PRAGMA foreign_keys=ON` y `PRAGMA journal_mode=WAL` en cada conexión

---

## 7. Providers

Las interfaces abstractas en `providers/base.py` son el contrato. Ver `DESIGN.md §10`.

Reglas:
- Todo provider implementa la interfaz abstracta completa
- La selección de provider ocurre en `providers/factory.py` por variable de entorno
- Agregar un provider nuevo requiere: implementar la interfaz → agregar case en factory → actualizar `.env.example` → actualizar tabla de stack en `DESIGN.md`

---

## 8. Manejo de errores

- Excepciones de dominio definidas en `services/exceptions.py`, heredan de `SpeakWiseError`
- Los routers capturan excepciones de dominio y las convierten en `HTTPException` con mensajes útiles
- Los servicios lanzan excepciones de dominio, nunca `HTTPException`
- Mensajes de error siempre incluyen: qué falló + por qué + qué hacer

---

## 9. Logging

- `import logging; logger = logging.getLogger(__name__)` en cada módulo
- Nunca `print()`
- Niveles: `DEBUG` = detalles de desarrollo, `INFO` = flujo normal, `WARNING` = inesperado pero no roto, `ERROR` = algo falló

---

## 10. Configuración

- Todo en `config.py`
- Variables con default razonable: `os.getenv("WHISPER_MODEL", "base")`
- Variables obligatorias: lanzar `EnvironmentError` con mensaje claro si faltan
- Nunca leer `os.getenv()` directamente en servicios o providers — siempre importar de `config.py`

---

## 11. Audio y código CPU-bound

- Archivos temporales siempre con `tempfile.NamedTemporaryFile(delete=True)` dentro de `with`
- librosa, Parselmouth y WhisperX son síncronos — ejecutar en `ThreadPoolExecutor` para no bloquear el event loop
- Un `ThreadPoolExecutor` compartido en `acoustic.py`, no uno por llamada

---

## 12. Commits

Formato: `tipo(scope): descripción en minúsculas`

| Tipo | Cuándo |
|---|---|
| `feat` | nueva funcionalidad |
| `fix` | corrección de bug |
| `refactor` | mejora sin cambiar comportamiento |
| `test` | agregar o corregir tests |
| `docs` | solo documentación |
| `chore` | dependencias, config |

---

## 13. Checklist antes de marcar un task como ✅

```
□ Type hints en todas las funciones del task
□ Sin print() — solo logger.*
□ Sin strings mágicos — todo en config.py o constantes
□ SQL usa parámetros (?, :param) — nunca f-strings
□ Archivos temporales en context manager
□ Código CPU-bound en ThreadPoolExecutor
□ Errores con mensajes útiles (qué + por qué)
□ Módulo no viola las reglas de dependencia
□ Al menos un test o verificación del comportamiento principal
□ DESIGN.md actualizado si cambió schema, API o estructura
```

---

## Historial

| Versión | Fecha | Cambio |
|---|---|---|
| 1.0 | Jul 2025 | Documento inicial |
| 1.1 | Jul 2025 | Recorte post-auditoría: eliminados bloques de código de implementación, corregido get_db vs @contextmanager, clarificado acoustic_service como dependency |
