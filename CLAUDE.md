# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Current state of this repository

This repository does **not yet contain the SpeakWise project code**. The only file present is `SETUP.md`, a Spanish-language provisioning checklist for bootstrapping the project from scratch on Windows. There is no `backend/`, `frontend/`, `pyproject.toml`, `Dockerfile`, etc. yet — those are all created *by* following `SETUP.md`, whose file contents are embedded inline in that document (see "ARCHIVOS DEL PROYECTO" section: ARCHIVO A–G).

If asked to set up, initialize, or start developing SpeakWise, follow `SETUP.md` — it is the source of truth for both the intended file structure and the exact contents of each config/scaffold file. Do not invent a different project layout.

**When SpeakWise code eventually exists in this repo, update this CLAUDE.md** with real architecture notes (module boundaries, data flow between STT/LLM/TTS providers, etc.) — the notes below are inferred from the setup plan, not from actual code.

## What SpeakWise is (per SETUP.md)

SpeakWise is a FastAPI backend + static frontend app, run via Docker Compose, intended as a speech-related tool (STT → LLM → TTS pipeline, per the env vars). Target root: `C:\dev\speakwise\` (a sibling location, not this repo).

Planned structure:
```
speakwise/
├── backend/          # FastAPI app (backend/main.py is the entrypoint: backend.main:app)
├── frontend/          # Static frontend, served by FastAPI's StaticFiles at "/"
├── corpus/            # (empty scaffold dir, purpose TBD)
├── templates/          # (empty scaffold dir, purpose TBD)
├── pyproject.toml
├── Dockerfile
├── docker-compose.yml
├── .dockerignore
└── .env / .env.example
```

Config surface (`.env.example`), showing the intended provider architecture:
```
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
This implies pluggable STT/TTS/LLM providers selected by env var — when the real code exists, look for a provider abstraction/factory pattern around these three concerns.

Dependencies (from `pyproject.toml` in SETUP.md, ARCHIVO E):
- **api** extras: fastapi, uvicorn, anthropic, openai, librosa, soundfile, praat-parselmouth, jinja2, python-multipart, aiofiles, cmudict, numpy<2.0 (pinned — librosa/praat-parselmouth aren't numpy 2.x compatible yet)
- **local** extras (adds to api): faster-whisper, kokoro — for running STT/TTS locally instead of via cloud APIs

This dependency mix (librosa, praat-parselmouth, cmudict) indicates real audio/phonetic analysis is part of the product, not just STT/TTS passthrough.

## Bootstrapping the environment

Follow `SETUP.md` phase by phase (FASE 0–7); it's designed to be executed sequentially by an AI agent, with explicit checkbox/expected-output verification per step. Key points if driving this:

- All commands are **PowerShell** (not CMD, not bash), on Windows.
- Requires WSL2 + Docker Desktop (Docker's WSL2 backend), enabled via `dism.exe` + reboot in FASE 1.
- The project itself has no repo yet at the target location — FASE 3 creates the directory tree from scratch (`New-Item`), it does not `git clone`.
- FASE 4 requires manually writing real API keys into `.env` (copied from `.env.example`) — `ANTHROPIC_API_KEY` and `OPENAI_API_KEY` — this step cannot be automated/verified beyond checking the keys are non-empty.
- FASE 5 builds and runs via Docker Compose; first build takes 10-15 min (installs ffmpeg, libsndfile1, build-essential, then pip installs).

## Common commands (once the project is bootstrapped, from `C:\dev\speakwise\`)

```powershell
docker compose up -d              # start in background
docker compose down               # stop (data preserved)
docker compose down --volumes     # stop AND delete the database
docker compose restart            # restart without losing data
docker compose logs -f            # live logs (Ctrl+C to exit)
docker compose build              # rebuild (after Dockerfile/pyproject.toml changes)
docker compose build --no-cache   # rebuild from scratch
docker compose exec speakwise bash   # shell inside the container
docker compose ps                    # check status
```

Hot reload is enabled via `--reload --reload-dir backend` in the compose `command:`, backed by a bind mount (`./backend:/app/backend`) — editing `backend/*.py` on the host should reload the running container within ~2s.

Health check: `GET http://localhost:8000/health` → `{"status":"ok","version":"1.0.0"}`. This is the canonical smoke test used throughout SETUP.md's verification steps.

## Mobile access (LAN)

The dev server binds `0.0.0.0:8000`, and SETUP.md's FASE 6 opens a Windows Firewall rule (`netsh advfirewall firewall add rule name="SpeakWise Dev" dir=in action=allow protocol=TCP localport=8000`) so it's reachable from a phone on the same WiFi via the host's LAN IP. Relevant when testing anything mobile/PWA-related.

## Troubleshooting reference

`SETUP.md` has a troubleshooting table at the end covering: Docker Desktop not started/PATH not reloaded, port 8000 already in use (`netstat -ano | findstr :8000` → `taskkill /PID ... /F`), Docker daemon unreachable, WSL2 kernel out of date (`wsl --update`), mobile firewall blocking, BIOS virtualization disabled, `pyproject.toml`/`main.py` scaffold errors. Consult it before improvising fixes to environment issues on this project.
