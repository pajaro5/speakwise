from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from backend.routers import progress, session
from backend.services.exceptions import InvalidLogEventError, ProviderUnavailableError

app = FastAPI(title="SpeakWise", version="1.0.0")


@app.get("/health")
async def health():
    """Endpoint de salud — usado por el script VALIDAR del SETUP."""
    return {"status": "ok", "version": "1.0.0"}


@app.exception_handler(ProviderUnavailableError)
async def provider_unavailable_handler(
    request: Request, exc: ProviderUnavailableError
) -> JSONResponse:
    return JSONResponse(status_code=503, content={"detail": str(exc)})


@app.exception_handler(EnvironmentError)
async def config_missing_handler(request: Request, exc: EnvironmentError) -> JSONResponse:
    # require() en config.py lanza EnvironmentError cuando falta una API key —
    # sin este handler el error queda como 500 sin manejar (bug real encontrado
    # probando /tutor a mano sin DEEPSEEK_API_KEY configurada).
    return JSONResponse(status_code=503, content={"detail": str(exc)})


@app.exception_handler(InvalidLogEventError)
async def invalid_log_event_handler(
    request: Request, exc: InvalidLogEventError
) -> JSONResponse:
    return JSONResponse(status_code=422, content={"detail": str(exc)})


app.include_router(session.router)
app.include_router(progress.router)

# Servir el frontend estático — va al final: es un catch-all en "/"
app.mount("/", StaticFiles(directory="frontend", html=True), name="static")
