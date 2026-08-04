"""Tests de integración contra APIs/modelos reales — no mockeados.

Excluidos del run normal y de CI (requieren API keys reales y, para
Kokoro, tiempo de carga del modelo). Correr manualmente antes de un
release: docker compose exec speakwise python -m pytest -m integration -v
"""

import pytest
from fastapi.testclient import TestClient

from backend.main import app


@pytest.fixture
def client():
    return TestClient(app)


@pytest.mark.integration
def test_tutor_with_real_deepseek_corrects_grammar(client: TestClient) -> None:
    response = client.post("/api/tutor", json={"text": "I go to work yesterday"})

    assert response.status_code == 200
    body = response.json()
    assert len(body["reply"]) > 0
    assert isinstance(body["session_id"], int)


@pytest.mark.integration
def test_speak_with_real_kokoro_returns_audio(client: TestClient) -> None:
    response = client.post("/api/speak", json={"text": "Great job! Try again."})

    assert response.status_code == 200
    assert response.headers["content-type"] == "audio/mpeg"
    assert len(response.content) > 1000
