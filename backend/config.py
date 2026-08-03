import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    stt_provider: str
    tts_provider: str
    llm_provider: str
    anthropic_api_key: str
    openai_api_key: str
    host: str
    port: int
    db_path: str
    api_cost_alert_usd: float


def load_settings() -> Settings:
    return Settings(
        stt_provider=os.getenv("STT_PROVIDER", "whisper_api"),
        tts_provider=os.getenv("TTS_PROVIDER", "openai"),
        llm_provider=os.getenv("LLM_PROVIDER", "claude"),
        anthropic_api_key=os.getenv("ANTHROPIC_API_KEY", ""),
        openai_api_key=os.getenv("OPENAI_API_KEY", ""),
        host=os.getenv("HOST", "0.0.0.0"),
        port=int(os.getenv("PORT", "8000")),
        db_path=os.getenv("DB_PATH", "/app/data/speakwise.db"),
        api_cost_alert_usd=float(os.getenv("API_COST_ALERT_USD", "30")),
    )


def require(value: str, var_name: str) -> str:
    if not value:
        raise EnvironmentError(
            f"{var_name} no está configurada en .env — "
            f"necesaria para el provider seleccionado. "
            f"Completá {var_name} en C:\\dev\\speakwise\\.env y reiniciá el contenedor."
        )
    return value
