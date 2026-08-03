import pytest

from backend.providers.factory import get_llm_provider, get_stt_provider, get_tts_provider
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
