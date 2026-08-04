from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from backend.routers import progress

app = FastAPI(title="SpeakWise", version="1.0.0")


@app.get("/health")
async def health():
    """Endpoint de salud — usado por el script VALIDAR del SETUP."""
    return {"status": "ok", "version": "1.0.0"}


app.include_router(progress.router)

# Servir el frontend estático — va al final: es un catch-all en "/"
app.mount("/", StaticFiles(directory="frontend", html=True), name="static")
