from pathlib import Path

FRONTEND_DIR = Path(__file__).resolve().parent.parent.parent / "frontend"


def _read(filename: str) -> str:
    return (FRONTEND_DIR / filename).read_text(encoding="utf-8")


def test_index_html_has_start_session_button() -> None:
    html = _read("index.html")
    assert 'id="start-session-btn"' in html


def test_index_html_has_three_module_containers() -> None:
    html = _read("index.html")
    assert 'id="module-1"' in html
    assert 'id="module-2"' in html
    assert 'id="module-3"' in html


def test_index_html_has_pattern_module_elements() -> None:
    html = _read("index.html")
    for element_id in ["pattern-name", "pattern-rule", "pattern-family", "listen-pattern-btn", "practice-pattern-btn"]:
        assert f'id="{element_id}"' in html, f"falta #{element_id}"


def test_index_html_has_chunk_module_elements() -> None:
    html = _read("index.html")
    for element_id in ["chunk-text", "listen-chunk-btn", "record-chunk-btn", "chunk-feedback"]:
        assert f'id="{element_id}"' in html, f"falta #{element_id}"


def test_app_js_calls_session_start_and_today() -> None:
    js = _read("app.js")
    assert '"/api/session/start"' in js
    assert '"/api/today"' in js


def test_app_js_calls_log_endpoint() -> None:
    js = _read("app.js")
    assert '"/api/log"' in js


def test_app_js_tutor_call_includes_session_id() -> None:
    js = _read("app.js")
    assert "sessionId" in js
