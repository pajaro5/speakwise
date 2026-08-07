import time

import pytest
from fastapi.testclient import TestClient

from backend import seed
from backend.database import db_connection, get_db
from backend.main import app


@pytest.fixture
def client(tmp_path):
    db_path = str(tmp_path / "progress_test.db")
    seed.run(db_path)

    def override_get_db():
        with db_connection(db_path) as conn:
            yield conn

    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app)
    app.dependency_overrides.clear()


def test_today_returns_200_with_full_contract(client: TestClient) -> None:
    response = client.get("/api/today")

    assert response.status_code == 200
    body = response.json()
    assert set(body.keys()) == {
        "week_words", "pattern_focus", "chunk_today", "difficulty", "topic_options",
        "conversation_starters", "linking_words",
    }
    assert len(body["topic_options"]) == 3
    assert len(body["conversation_starters"]) == 3
    assert len(body["linking_words"]) == 3


def test_today_week_words_match_contract_shape(client: TestClient) -> None:
    response = client.get("/api/today")
    body = response.json()

    assert len(body["week_words"]) <= 5
    for w in body["week_words"]:
        assert set(w.keys()) == {"form", "tense", "lfc_focus", "score"}


def test_today_pattern_focus_matches_contract_shape(client: TestClient) -> None:
    response = client.get("/api/today")
    body = response.json()

    assert set(body["pattern_focus"].keys()) == {
        "id", "name", "rule_es", "rule_ipa", "family", "family_stress", "family_respelling",
    }


def test_today_chunk_matches_contract_shape(client: TestClient) -> None:
    response = client.get("/api/today")
    body = response.json()

    assert set(body["chunk_today"].keys()) == {"chunk", "function", "spontaneous_uses"}


def test_today_responds_under_500ms_with_real_seeded_data(client: TestClient) -> None:
    start = time.perf_counter()
    response = client.get("/api/today")
    elapsed_ms = (time.perf_counter() - start) * 1000

    assert response.status_code == 200
    assert elapsed_ms < 500


def test_panel_returns_501_not_implemented(client: TestClient) -> None:
    response = client.get("/api/panel")
    assert response.status_code == 501


def test_progress_returns_501_not_implemented(client: TestClient) -> None:
    response = client.get("/api/progress")
    assert response.status_code == 501


def test_stats_returns_501_not_implemented(client: TestClient) -> None:
    response = client.get("/api/stats")
    assert response.status_code == 501
