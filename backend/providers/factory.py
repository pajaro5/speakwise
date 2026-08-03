from backend.config import load_settings, require
from backend.providers.base import LLMProvider, STTProvider, TTSProvider
from backend.services.exceptions import UnknownProviderError


def get_stt_provider() -> STTProvider:
    settings = load_settings()
    if settings.stt_provider == "whisper_api":
        key = require(settings.openai_api_key, "OPENAI_API_KEY")
        from backend.providers.stt_whisper_api import WhisperAPIProvider

        return WhisperAPIProvider(api_key=key)
    raise UnknownProviderError(f"STT_PROVIDER desconocido: {settings.stt_provider!r}")


def get_tts_provider() -> TTSProvider:
    settings = load_settings()
    if settings.tts_provider == "openai":
        key = require(settings.openai_api_key, "OPENAI_API_KEY")
        from backend.providers.tts_openai import OpenAITTSProvider

        return OpenAITTSProvider(api_key=key)
    raise UnknownProviderError(f"TTS_PROVIDER desconocido: {settings.tts_provider!r}")


def get_llm_provider() -> LLMProvider:
    settings = load_settings()
    if settings.llm_provider == "claude":
        key = require(settings.anthropic_api_key, "ANTHROPIC_API_KEY")
        from backend.providers.llm_claude import ClaudeProvider

        return ClaudeProvider(api_key=key)
    raise UnknownProviderError(f"LLM_PROVIDER desconocido: {settings.llm_provider!r}")
