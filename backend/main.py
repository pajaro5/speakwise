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
