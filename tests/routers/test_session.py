import asyncio
import time

import pytest
from fastapi.testclient import TestClient

from backend.database import db_connection, get_db
from backend.main import app
from backend.providers.base import LLMProvider, STTProvider, TTSProvider, Transcript
from backend.routers import session as session_router
from backend.services.exceptions import ProviderUnavailableError


class _FakeSTTProvider(STTProvider):
    async def transcribe(self, audio: bytes) -> Transcript:
        words = [
            {"w": "I", "start": 0.0, "end": 0.2},
            {"w": "go", "start": 0.2, "end": 3.4},
        ]
        return Transcript(text="I go", wpm=0.0, words=words)


class _FakeTTSProvider(TTSProvider):
    async def synthesize(self, text: str, voice: str = "default") -> bytes:
        return b"FAKE-AUDIO-BYTES"


class _FakeLLMProvider(LLMProvider):
    async def complete(self, messages: list, system: str, max_tokens: int = 400) -> str:
        return "Great try! Next time say 'I went to work yesterday'."


@pytest.fixture
def client(tmp_path):
    db_path = str(tmp_path / "session_test.db")

    def override_get_db():
        with db_connection(db_path) as conn:
            yield conn

    app.dependency_overrides[session_router.get_stt_provider] = lambda: _FakeSTTProvider()
    app.dependency_overrides[session_router.get_tts_provider] = lambda: _FakeTTSProvider()
    app.dependency_overrides[session_router.get_llm_provider] = lambda: _FakeLLMProvider()
    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app), db_path
    app.dependency_overrides.clear()


def test_transcribe_returns_200_with_contract_shape(client) -> None:
    test_client, _ = client
    response = test_client.post(
        "/api/transcribe",
        files={"audio": ("audio.webm", b"fake-webm-bytes", "audio/webm")},
    )

    assert response.status_code == 200
    body = response.json()
    assert set(body.keys()) == {"text", "wpm", "fillers", "words"}
    assert body["text"] == "I go"


def test_transcribe_without_audio_returns_422(client) -> None:
    test_client, _ = client
    response = test_client.post("/api/transcribe")

    assert response.status_code == 422


def test_speak_returns_200_with_audio_bytes(client) -> None:
    test_client, _ = client
    response = test_client.post("/api/speak", json={"text": "Great job!"})

    assert response.status_code == 200
    assert response.content == b"FAKE-AUDIO-BYTES"
    assert response.headers["content-type"].startswith("audio/")


def test_tutor_returns_200_with_reply_and_session_id(client) -> None:
    test_client, _ = client
    response = test_client.post("/api/tutor", json={"text": "I go to work yesterday"})

    assert response.status_code == 200
    body = response.json()
    assert set(body.keys()) == {"reply", "session_id"}
    assert "went" in body["reply"]
    assert isinstance(body["session_id"], int)


def test_tutor_persists_session_in_sqlite(client) -> None:
    test_client, db_path = client
    response = test_client.post(
        "/api/tutor",
        json={"text": "I go to work yesterday", "topic": "tu semana", "wpm": 85.5, "fillers": 1},
    )
    session_id = response.json()["session_id"]

    with db_connection(db_path) as conn:
        row = conn.execute("SELECT * FROM sessions WHERE id = ?", (session_id,)).fetchone()

    assert row is not None
    assert row["topic"] == "tu semana"
    assert row["transcript"] == "I go to work yesterday"
    assert row["wpm"] == 85.5
    assert row["fillers"] == 1
    assert "went" in row["feedback"]


def test_tutor_reuses_session_id_updates_instead_of_duplicating(client) -> None:
    test_client, db_path = client
    first = test_client.post("/api/tutor", json={"text": "I go yesterday"})
    session_id = first.json()["session_id"]

    second = test_client.post(
        "/api/tutor", json={"text": "I went yesterday", "session_id": session_id}
    )

    assert second.json()["session_id"] == session_id
    with db_connection(db_path) as conn:
        count = conn.execute("SELECT COUNT(*) FROM sessions").fetchone()[0]
        row = conn.execute(
            "SELECT transcript FROM sessions WHERE id = ?", (session_id,)
        ).fetchone()

    assert count == 1
    assert row["transcript"] == "I went yesterday"


def test_tutor_returns_503_when_llm_provider_down(client) -> None:
    test_client, _ = client

    class _BrokenLLM(LLMProvider):
        async def complete(self, messages, system, max_tokens=400) -> str:
            raise ProviderUnavailableError("Claude API no disponible: timeout")

    app.dependency_overrides[session_router.get_llm_provider] = lambda: _BrokenLLM()

    response = test_client.post("/api/tutor", json={"text": "hola"})

    assert response.status_code == 503
    assert "no disponible" in response.json()["detail"]


def test_tutor_returns_clean_error_when_api_key_missing(client) -> None:
    test_client, _ = client

    def _broken_get_llm_provider():
        raise EnvironmentError(
            "DEEPSEEK_API_KEY no está configurada en .env — necesaria para el "
            "provider seleccionado."
        )

    app.dependency_overrides[session_router.get_llm_provider] = _broken_get_llm_provider

    response = test_client.post("/api/tutor", json={"text": "hola"})

    assert response.status_code == 503
    assert "DEEPSEEK_API_KEY" in response.json()["detail"]


def test_transcribe_returns_503_when_stt_provider_down(client) -> None:
    test_client, _ = client

    class _BrokenSTT(STTProvider):
        async def transcribe(self, audio: bytes) -> Transcript:
            raise ProviderUnavailableError("Whisper local no disponible: modelo no cargó")

    app.dependency_overrides[session_router.get_stt_provider] = lambda: _BrokenSTT()

    response = test_client.post(
        "/api/transcribe",
        files={"audio": ("audio.webm", b"fake-bytes", "audio/webm")},
    )

    assert response.status_code == 503


def test_full_cycle_transcribe_tutor_speak_under_10_seconds(client) -> None:
    test_client, _ = client

    class _SlowSTT(STTProvider):
        async def transcribe(self, audio: bytes) -> Transcript:
            await asyncio.sleep(2)
            return Transcript(
                text="I go to work yesterday",
                wpm=0.0,
                words=[{"w": "I", "start": 0.0, "end": 0.2}],
            )

    class _SlowLLM(LLMProvider):
        async def complete(self, messages, system, max_tokens=400) -> str:
            await asyncio.sleep(3)
            return "Try 'I went to work yesterday' instead."

    class _SlowTTS(TTSProvider):
        async def synthesize(self, text: str, voice: str = "default") -> bytes:
            await asyncio.sleep(1)
            return b"AUDIO-BYTES"

    app.dependency_overrides[session_router.get_stt_provider] = lambda: _SlowSTT()
    app.dependency_overrides[session_router.get_llm_provider] = lambda: _SlowLLM()
    app.dependency_overrides[session_router.get_tts_provider] = lambda: _SlowTTS()

    start = time.perf_counter()

    transcribe_resp = test_client.post(
        "/api/transcribe",
        files={"audio": ("audio.webm", b"fake-bytes", "audio/webm")},
    )
    text = transcribe_resp.json()["text"]

    tutor_resp = test_client.post("/api/tutor", json={"text": text})
    reply = tutor_resp.json()["reply"]

    speak_resp = test_client.post("/api/speak", json={"text": reply})

    elapsed = time.perf_counter() - start

    assert transcribe_resp.status_code == 200
    assert tutor_resp.status_code == 200
    assert speak_resp.status_code == 200
    assert elapsed < 10.0
