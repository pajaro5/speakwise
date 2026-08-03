import pytest

from backend.config import load_settings, require


def test_load_settings_uses_defaults_when_env_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    for var in [
        "STT_PROVIDER", "TTS_PROVIDER", "LLM_PROVIDER",
        "ANTHROPIC_API_KEY", "OPENAI_API_KEY",
        "HOST", "PORT", "DB_PATH", "API_COST_ALERT_USD",
    ]:
        monkeypatch.delenv(var, raising=False)

    settings = load_settings()

    assert settings.stt_provider == "whisper_api"
    assert settings.tts_provider == "openai"
    assert settings.llm_provider == "claude"
    assert settings.anthropic_api_key == ""
    assert settings.openai_api_key == ""
    assert settings.host == "0.0.0.0"
    assert settings.port == 8000
    assert settings.db_path == "/app/data/speakwise.db"
    assert settings.api_cost_alert_usd == 30.0


def test_load_settings_reads_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LLM_PROVIDER", "ollama_qwen")
    monkeypatch.setenv("PORT", "9000")

    settings = load_settings()

    assert settings.llm_provider == "ollama_qwen"
    assert settings.port == 9000


def test_require_raises_with_clear_message_when_missing() -> None:
    with pytest.raises(EnvironmentError, match="ANTHROPIC_API_KEY"):
        require("", "ANTHROPIC_API_KEY")


def test_require_returns_value_when_present() -> None:
    assert require("sk-real-key", "ANTHROPIC_API_KEY") == "sk-real-key"
