# SETUP — Entorno de desarrollo Windows · SpeakWise

> v2.0 — Corregido tras auditoría · 5 críticos + 6 importantes resueltos

---

## Protocolo de ejecución para Claude

```
REGLAS ESTRICTAS
────────────────────────────────────────────────────────────────
1. Leer cada tabla de ARRIBA hacia ABAJO
2. Ejecutar el primer paso con estado  ⬜
3. Comparar la salida real con la columna  ESPERADO
4. Si coincide   → reemplazar ⬜ por ✅  en este documento
5. Si NO coincide → ir a TROUBLESHOOTING al final
6. Continuar con el siguiente ⬜
7. NO saltar pasos aunque parezcan obvios
8. Al finalizar → ejecutar el bloque VALIDAR
────────────────────────────────────────────────────────────────

CONVENCIONES
  [ADMIN]  = PowerShell abierto como Administrador
  [USER]   = PowerShell sin elevación
  [DIR]    = PowerShell en C:\dev\speakwise\
  Todos los comandos son PowerShell. No usar CMD.
```

---

## FASE 0 — Verificar el sistema

> Abrir PowerShell como Administrador.

| # | Verificación | Comando `[ADMIN]` | Esperado | ✓ |
|---|---|---|---|---|
| 0.1 | Versión Windows | `(Get-WmiObject Win32_OperatingSystem).Caption` | Contiene `Windows 10` o `Windows 11` | ⬜ |
| 0.2 | Virtualización en firmware | `(systeminfo) \| Select-String "Virtualization Enabled In Firmware"` | `Virtualization Enabled In Firmware:  Yes` | ⬜ |
| 0.3 | RAM disponible | `[math]::Round((Get-ComputerInfo).TotalPhysicalMemory/1GB,1)` | `≥ 8` | ⬜ |
| 0.4 | Espacio libre en C: | `[math]::Round((Get-PSDrive C).Free/1GB,1)` | `≥ 15` | ⬜ |
| 0.5 | winget disponible | `winget --version` | `v1.x.x` | ⬜ |

**Si 0.2 muestra `No`:** reiniciar → BIOS (`F2` o `Del`) → habilitar Intel VT-x o AMD-V.  
**Si 0.5 falla:** actualizar Windows o instalar winget desde `https://aka.ms/winget-cli`

---

## FASE 1 — Instalar herramientas del sistema

| # | Acción | Comando `[ADMIN]` | Esperado | ✓ |
|---|---|---|---|---|
| 1.1 | Habilitar WSL | `dism.exe /online /enable-feature /featurename:Microsoft-Windows-Subsystem-Linux /all /norestart` | `The operation completed successfully.` | ⬜ |
| 1.2 | Habilitar Virtual Machine Platform | `dism.exe /online /enable-feature /featurename:VirtualMachinePlatform /all /norestart` | `The operation completed successfully.` | ⬜ |
| 1.3 | Reiniciar *(marcar 1.1 y 1.2 como ✅ antes)* | `shutdown /r /t 30` | PC se apaga en 30 segundos | ⬜ |
| 1.4 | Abrir PowerShell Admin después del reinicio | `([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)` | `True` | ⬜ |
| 1.5 | Actualizar kernel WSL2 | `wsl --update` | `The most recent version is already installed` o descarga e instala | ⬜ |
| 1.6 | WSL2 como versión por defecto | `wsl --set-default-version 2` | `For information on key differences...` | ⬜ |
| 1.7 | Instalar Docker Desktop | `winget install Docker.DockerDesktop` | `Successfully installed` | ⬜ |
| 1.8 | Instalar Git | `winget install Git.Git` | `Successfully installed` | ⬜ |
| 1.9 | Instalar VS Code | `winget install Microsoft.VisualStudioCode` | `Successfully installed` | ⬜ |
| 1.10 | `[OPCIONAL]` Windows Terminal | `winget install Microsoft.WindowsTerminal` | `Successfully installed` | ⬜ |
| 1.11 | Recargar PATH en sesión actual | `$env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")` | *(sin output — silencioso)* | ⬜ |
| 1.12 | Verificar Git en PATH | `git --version` | `git version 2.x.x` | ⬜ |
| 1.13 | Abrir Docker Desktop | *(menú inicio → Docker Desktop)* | Ícono de ballena en barra de tareas | ⬜ |
| 1.14 | Esperar a que Docker esté listo | *(esperar 2-3 minutos)* | Ícono de ballena **verde** (no animado) | ⬜ |

---

## FASE 2 — Verificar Docker

| # | Acción | Comando `[USER]` | Esperado | ✓ |
|---|---|---|---|---|
| 2.1 | Versión Docker | `docker --version` | `Docker version 24.x.x` o superior | ⬜ |
| 2.2 | Versión Compose | `docker compose version` | `Docker Compose version v2.x.x` | ⬜ |
| 2.3 | Docker Engine funciona | `docker run hello-world` | Mensaje `Hello from Docker!` | ⬜ |
| 2.4 | WSL2 backend activo | `$info = docker info; ($info -join " ") -match "WSL"` | `True` | ⬜ |

---

## FASE 3 — Crear estructura del proyecto

> El proyecto no tiene repositorio aún. Esta fase crea toda la estructura desde cero.

| # | Acción | Comando `[USER]` | Esperado | ✓ |
|---|---|---|---|---|
| 3.1 | Crear directorio base | `New-Item -ItemType Directory -Force C:\dev` | Directorio creado | ⬜ |
| 3.2 | Crear raíz del proyecto | `New-Item -ItemType Directory -Force C:\dev\speakwise` | Directorio creado | ⬜ |
| 3.3 | Crear subdirectorios | `New-Item -ItemType Directory -Force C:\dev\speakwise\backend, C:\dev\speakwise\frontend, C:\dev\speakwise\corpus, C:\dev\speakwise\templates` | 4 directorios creados | ⬜ |
| 3.4 | Ir al proyecto | `cd C:\dev\speakwise` | Prompt muestra `C:\dev\speakwise>` | ⬜ |
| 3.5 | Crear `backend\__init__.py` vacío | `New-Item -ItemType File -Force backend\__init__.py` | Archivo creado | ⬜ |
| 3.6 | Verificar estructura | `Get-ChildItem -Name` | Ver: `backend  frontend  corpus  templates` | ⬜ |

---

## FASE 4 — Archivos de configuración

> Crear cada archivo copiando el contenido desde la sección **ARCHIVOS DEL PROYECTO** al final de este documento.  
> Abrir VS Code con `code .` `[DIR]` para editar cómodamente.

| # | Archivo | Ruta destino | Verificación `[DIR]` | ✓ |
|---|---|---|---|---|
| 4.1 | `pyproject.toml` → **ARCHIVO E** | `C:\dev\speakwise\pyproject.toml` | `Test-Path pyproject.toml` → `True` | ⬜ |
| 4.2 | `backend\main.py` → **ARCHIVO F** | `C:\dev\speakwise\backend\main.py` | `Test-Path backend\main.py` → `True` | ⬜ |
| 4.3 | `frontend\index.html` → **ARCHIVO G** | `C:\dev\speakwise\frontend\index.html` | `Test-Path frontend\index.html` → `True` | ⬜ |
| 4.4 | `.env.example` → **ARCHIVO D** | `C:\dev\speakwise\.env.example` | `Test-Path .env.example` → `True` | ⬜ |
| 4.5 | Crear `.env` desde la plantilla | `Copy-Item .env.example .env` `[DIR]` | `Test-Path .env` → `True` | ⬜ |
| 4.6 | Editar `.env` con API keys reales | `code .env` `[DIR]` → editar → guardar | Valores no vacíos en ambas keys | ⬜ |
| 4.7 | Verificar `.env` tiene valores | `Select-String -Path .env -Pattern "API_KEY=.+"` `[DIR]` | Muestra 2 líneas con valores | ⬜ |
| 4.8 | `Dockerfile` → **ARCHIVO A** | `C:\dev\speakwise\Dockerfile` | `Test-Path Dockerfile` → `True` | ⬜ |
| 4.9 | `docker-compose.yml` → **ARCHIVO B** | `C:\dev\speakwise\docker-compose.yml` | `Test-Path docker-compose.yml` → `True` | ⬜ |
| 4.10 | `.dockerignore` → **ARCHIVO C** | `C:\dev\speakwise\.dockerignore` | `Test-Path .dockerignore` → `True` | ⬜ |
| 4.11 | Verificar todos los archivos | `Get-ChildItem -Name` `[DIR]` | Ver: `backend  frontend  corpus  templates  .dockerignore  .env  .env.example  Dockerfile  docker-compose.yml  pyproject.toml` | ⬜ |

---

## FASE 5 — Build y ejecución

> ⚠ El primer build descarga la imagen base de Python (~200MB) e instala paquetes. Puede tardar **10-15 minutos**. Es normal si no hay output visible durante ese tiempo.

| # | Acción | Comando `[DIR]` | Esperado | ✓ |
|---|---|---|---|---|
| 5.1 | Build de la imagen | `docker compose build` | Última línea contiene `Successfully built` | ⬜ |
| 5.2 | Iniciar contenedor | `docker compose up -d` | `Container speakwise-speakwise-1  Started` | ⬜ |
| 5.3 | Verificar estado | `docker compose ps` | Columna `STATUS` muestra `running` | ⬜ |
| 5.4 | Ver log de inicio | `docker compose logs speakwise` | `Uvicorn running on http://0.0.0.0:8000` | ⬜ |
| 5.5 | Test en browser | *(abrir `http://localhost:8000` en Chrome)* | Página con `SpeakWise — En desarrollo` | ⬜ |
| 5.6 | Test endpoint health | `(Invoke-WebRequest http://localhost:8000/health).StatusCode` | `200` | ⬜ |
| 5.7 | Test respuesta JSON | `(Invoke-WebRequest http://localhost:8000/health).Content` | `{"status":"ok","version":"1.0.0"}` | ⬜ |

---

## FASE 6 — Acceso desde móvil

| # | Acción | Comando | Esperado | ✓ |
|---|---|---|---|---|
| 6.1 | Listar interfaces de red con IP | `Get-NetIPAddress -AddressFamily IPv4 \| Where-Object {$_.IPAddress -notmatch "^127\."} \| Select-Object IPAddress, InterfaceAlias` `[USER]` | Muestra lista de IPs — identificar la de la interfaz WiFi | ⬜ |
| 6.2 | Anotar la IP WiFi del PC | *(tomar nota de la IP del paso 6.1)* | IP del tipo `192.168.x.x` anotada | ⬜ |
| 6.3 | Abrir puerto en firewall | `netsh advfirewall firewall add rule name="SpeakWise Dev" dir=in action=allow protocol=TCP localport=8000` `[ADMIN]` | `Ok.` | ⬜ |
| 6.4 | Test desde el móvil | *(Chrome móvil → `http://[IP-anotada]:8000`)* | Página `SpeakWise — En desarrollo` carga en el móvil | ⬜ |
| 6.5 | `[OPCIONAL]` Instalar como PWA | *(Chrome móvil → menú ⋮ → Añadir a pantalla de inicio)* | Ícono aparece en la pantalla del móvil | ⬜ |

---

## [OPCIONAL] FASE 7 — VS Code extensiones

> Esta fase no es necesaria para desarrollar. Instalar cuando el entorno esté validado.

| # | Acción | Cómo | Esperado | ✓ |
|---|---|---|---|---|
| 7.1 | Abrir proyecto | `code .` `[DIR]` | VS Code abre con la carpeta `speakwise` | ⬜ |
| 7.2 | Extensión Docker | Extensions (`Ctrl+Shift+X`) → `ms-azuretools.vscode-docker` → Install | Instalada | ⬜ |
| 7.3 | Extensión Python | Extensions → `ms-python.python` → Install | Instalada | ⬜ |
| 7.4 | Extensión SQLite Viewer | Extensions → `qwtel.sqlite-viewer` → Install | Instalada | ⬜ |
| 7.5 | Verificar hot reload | Editar y guardar `backend\main.py` | `docker compose logs -f` muestra `Reloading...` en < 2 segundos | ⬜ |

---

## VALIDAR — Script de verificación final

Ejecutar desde `[DIR]`. **Todos los ítems deben mostrar ✅** antes de empezar a desarrollar:

```powershell
Write-Host "`n=== Verificacion SpeakWise ===" -ForegroundColor Cyan
$ok = $true

# Docker
$dv = docker --version 2>$null
if ($dv) { Write-Host "✅ Docker:       $dv" }
else      { Write-Host "❌ Docker:       no disponible"; $ok = $false }

# Contenedor
$st = (docker compose ps --format "{{.Status}}" 2>$null)
if ($st -match "running") { Write-Host "✅ Contenedor:   running" }
else                       { Write-Host "❌ Contenedor:   $st"; $ok = $false }

# API /health
try {
    $r = Invoke-WebRequest -Uri "http://localhost:8000/health" -TimeoutSec 5 -EA Stop
    $body = $r.Content | ConvertFrom-Json
    if ($body.status -eq "ok") { Write-Host "✅ API health:   ok" }
    else { Write-Host "❌ API health:   respuesta inesperada: $($r.Content)"; $ok = $false }
} catch {
    Write-Host "❌ API health:   no responde en :8000"; $ok = $false
}

# Frontend
try {
    $f = Invoke-WebRequest -Uri "http://localhost:8000/" -TimeoutSec 5 -EA Stop
    Write-Host "✅ Frontend:     HTTP $($f.StatusCode)"
} catch {
    Write-Host "❌ Frontend:     no responde en :8000/"; $ok = $false
}

# IP WiFi para móvil
$ips = Get-NetIPAddress -AddressFamily IPv4 | Where-Object {$_.IPAddress -notmatch "^127\."}
if ($ips) {
    $ips | ForEach-Object { Write-Host "✅ Acceso móvil: http://$($_.IPAddress):8000  [$($_.InterfaceAlias)]" }
} else {
    Write-Host "⚠  Red:          no se detectó IP — verificar conexión"
}

# pyproject.toml
if (Test-Path pyproject.toml) { Write-Host "✅ pyproject:    existe" }
else                           { Write-Host "❌ pyproject:    falta — ver ARCHIVO E"; $ok = $false }

Write-Host ""
if ($ok) { Write-Host "ENTORNO LISTO ✅  — puedes empezar a desarrollar" -ForegroundColor Green }
else      { Write-Host "HAY ERRORES — revisar los ❌ y la tabla TROUBLESHOOTING" -ForegroundColor Red }
Write-Host "==============================`n" -ForegroundColor Cyan
```

---

## ARCHIVOS DEL PROYECTO

### ARCHIVO A — `Dockerfile`

```dockerfile
FROM python:3.11-slim

RUN apt-get update && apt-get install -y \
    ffmpeg \
    libsndfile1 \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY pyproject.toml .
RUN pip install --no-cache-dir -e ".[api]"

COPY . .

RUN mkdir -p /app/data

EXPOSE 8000

CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

---

### ARCHIVO B — `docker-compose.yml`

```yaml
services:
  speakwise:
    build: .
    ports:
      - "8000:8000"
    volumes:
      - ./backend:/app/backend
      - ./frontend:/app/frontend
      - ./templates:/app/templates
      - ./corpus:/app/corpus
      - speakwise_data:/app/data
    env_file:
      - .env
    command: >
      uvicorn backend.main:app
      --host 0.0.0.0
      --port 8000
      --reload
      --reload-dir backend
    restart: unless-stopped

volumes:
  speakwise_data:
```

---

### ARCHIVO C — `.dockerignore`

```
.env
.git
.gitignore
__pycache__
*.pyc
*.pyo
.pytest_cache
speakwise.db
*.db
.DS_Store
Thumbs.db
```

---

### ARCHIVO D — `.env.example`

*(Se commitea al repo. Sin valores reales.)*

```bash
STT_PROVIDER=whisper_api
TTS_PROVIDER=openai
LLM_PROVIDER=claude

ANTHROPIC_API_KEY=
OPENAI_API_KEY=

HOST=0.0.0.0
PORT=8000
DB_PATH=/app/data/speakwise.db
API_COST_ALERT_USD=30
```

---

### ARCHIVO E — `pyproject.toml`

```toml
[build-system]
requires = ["setuptools>=68"]
build-backend = "setuptools.backends.legacy:build"

[project]
name = "speakwise"
version = "1.0.0"
requires-python = ">=3.11"

[tool.setuptools.packages.find]
where = ["."]
include = ["backend*"]

[project.optional-dependencies]
api = [
    "fastapi>=0.111",
    "uvicorn[standard]>=0.29",
    "anthropic>=0.28",
    "openai>=1.30",
    "librosa>=0.10",
    "soundfile>=0.12",
    "praat-parselmouth>=0.4",
    "jinja2>=3.1",
    "python-multipart>=0.0.9",
    "aiofiles>=23.0",
    "cmudict>=1.0",
    "numpy<2.0",
]
local = [
    "speakwise[api]",
    "faster-whisper>=1.0",
    "kokoro>=0.3",
]
```

> `numpy<2.0` — librosa y praat-parselmouth aún no son compatibles con numpy 2.x.

---

### ARCHIVO F — `backend/main.py`

*(Versión mínima para validar el entorno. Se expande durante el desarrollo.)*

```python
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse

app = FastAPI(title="SpeakWise", version="1.0.0")


@app.get("/health")
async def health():
    """Endpoint de salud — usado por el script VALIDAR del SETUP."""
    return {"status": "ok", "version": "1.0.0"}


# Servir el frontend estático
app.mount("/", StaticFiles(directory="frontend", html=True), name="static")
```

---

### ARCHIVO G — `frontend/index.html`

*(Placeholder visual. Se reemplaza durante el desarrollo del frontend.)*

```html
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>SpeakWise</title>
    <style>
        body { font-family: system-ui, sans-serif; max-width: 500px;
               margin: 100px auto; text-align: center; color: #1e293b; }
        h1   { color: #2563eb; font-size: 2rem; }
        code { background: #f1f5f9; padding: 2px 8px; border-radius: 4px; }
    </style>
</head>
<body>
    <h1>🎙️ SpeakWise</h1>
    <p>Servidor activo. Entorno de desarrollo listo.</p>
    <p><code>GET /health → {"status": "ok"}</code></p>
</body>
</html>
```

---

## TROUBLESHOOTING

| Síntoma | Diagnóstico | Solución |
|---|---|---|
| `docker: command not found` | Docker Desktop no iniciado o PATH no recargado | Abrir Docker Desktop → esperar ícono verde. Si persiste: ejecutar paso 1.11 |
| `port 8000 is already in use` | Puerto ocupado | `netstat -ano \| findstr :8000` → `taskkill /PID [número] /F` `[ADMIN]` |
| `Cannot connect to Docker daemon` | Docker Desktop cerrado | Abrir Docker Desktop → esperar ícono verde |
| `WSL2 kernel update required` | Kernel desactualizado | `wsl --update` `[ADMIN]` |
| Móvil no conecta | Firewall bloquea el puerto | Ejecutar paso 6.3 |
| `Virtualization Enabled In Firmware: No` | BIOS sin virtualización | Reiniciar → BIOS (`F2`/`Del`) → habilitar Intel VT-x o AMD-V |
| Build falla: `No module named 'setuptools'` | Imagen base desactualizada | `docker compose build --no-cache` |
| Build falla: `Could not find a version that satisfies` | Paquete no existe en PyPI | Verificar nombre exacto en `pyproject.toml` ARCHIVO E |
| `Test-Path .env.example` → `False` | `.env.example` no creado aún | Crear ARCHIVO D primero, luego ejecutar paso 4.5 |
| `(Invoke-WebRequest).StatusCode` → `404` | Ruta `/health` no existe en `main.py` | Verificar que ARCHIVO F fue guardado correctamente |
| Hot reload no funciona | Volumen no montado | Verificar `./backend:/app/backend` en `docker-compose.yml` |
| winget falla con error de red | Sin internet o proxy | Descargar instaladores `.exe` desde docker.com y git-scm.com |

---

## COMANDOS RÁPIDOS

```powershell
# Desde C:\dev\speakwise\

docker compose up -d              # iniciar en background
docker compose down               # detener (datos se conservan)
docker compose down --volumes     # ⚠ detener Y borrar la base de datos
docker compose restart            # reiniciar sin perder datos
docker compose logs -f            # logs en tiempo real (Ctrl+C para salir)
docker compose build              # rebuildar (cuando cambia Dockerfile o pyproject.toml)
docker compose build --no-cache   # rebuildar desde cero
docker compose exec speakwise bash   # shell dentro del contenedor
docker compose ps                    # ver estado
```

---

## HISTORIAL

| Versión | Fecha | Cambio |
|---|---|---|
| 1.0 | Jul 2025 | Windows · MVP APIs cloud · Tablas con ⬜/✅ para IA |
| 2.0 | Jul 2025 | Corrección post-auditoría: +pyproject.toml, +main.py, +index.html, reemplaza git clone por creación desde cero, fix virtualización, fix PATH, fix WiFi, fix .env circular, fix pipe en tablas |
