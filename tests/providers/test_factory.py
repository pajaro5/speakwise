import pytest

from backend.providers.factory import get_llm_provider, get_stt_provider, get_tts_provider
from backend.providers.llm_deepseek import DeepSeekProvider
from backend.providers.llm_ollama import OllamaProvider
from backend.providers.stt_whisperx import WhisperXLocalProvider
from backend.providers.tts_kokoro import KokoroTTSProvider
from backend.services.exceptions import UnknownProviderError


def test_get_stt_provider_raises_on_unknown_provider(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("STT_PROVIDER", "not_a_real_provider")
    with pytest.raises(UnknownProviderError, match="not_a_real_provider"):
        get_stt_provider()


def test_get_tts_provider_raises_on_unknown_provider(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TTS_PROVIDER", "not_a_real_provider")
    with pytest.raises(UnknownProviderError, match="not_a_real_provider"):
        get_tts_provider()


def test_get_llm_provider_raises_on_unknown_provider(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LLM_PROVIDER", "not_a_real_provider")
    with pytest.raises(UnknownProviderError, match="not_a_real_provider"):
        get_llm_provider()


def test_get_llm_provider_requires_api_key_before_import(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LLM_PROVIDER", "claude")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "")
    with pytest.raises(EnvironmentError, match="ANTHROPIC_API_KEY"):
        get_llm_provider()


def test_get_stt_provider_returns_local_whisper_by_default() -> None:
    assert isinstance(get_stt_provider(), WhisperXLocalProvider)


def test_get_tts_provider_returns_kokoro_by_default() -> None:
    assert isinstance(get_tts_provider(), KokoroTTSProvider)


def test_get_llm_provider_defaults_to_deepseek_and_requires_its_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("LLM_PROVIDER", raising=False)
    monkeypatch.setenv("DEEPSEEK_API_KEY", "")
    with pytest.raises(EnvironmentError, match="DEEPSEEK_API_KEY"):
        get_llm_provider()


def test_get_llm_provider_returns_deepseek_when_key_present(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("LLM_PROVIDER", raising=False)
    monkeypatch.setenv("DEEPSEEK_API_KEY", "sk-fake-key")
    assert isinstance(get_llm_provider(), DeepSeekProvider)


def test_get_llm_provider_ollama_still_available_but_not_default(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("LLM_PROVIDER", "ollama_qwen")
    assert isinstance(get_llm_provider(), OllamaProvider)
