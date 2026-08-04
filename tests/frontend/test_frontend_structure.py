from pathlib import Path

FRONTEND_DIR = Path(__file__).resolve().parent.parent.parent / "frontend"


def _read(filename: str) -> str:
    return (FRONTEND_DIR / filename).read_text(encoding="utf-8")


def test_index_html_has_record_button() -> None:
    html = _read("index.html")
    assert 'id="record-btn"' in html


def test_index_html_loads_app_js() -> None:
    html = _read("index.html")
    assert '<script src="app.js"></script>' in html


def test_index_html_has_mobile_viewport() -> None:
    html = _read("index.html")
    assert 'name="viewport"' in html


def test_index_html_has_transcript_and_reply_display_areas() -> None:
    html = _read("index.html")
    assert 'id="transcript"' in html
    assert 'id="tutor-reply"' in html


def test_index_html_has_audio_playback_element() -> None:
    html = _read("index.html")
    assert 'id="tutor-audio"' in html


def test_app_js_uses_media_recorder_api() -> None:
    js = _read("app.js")
    assert "navigator.mediaDevices.getUserMedia" in js
    assert "MediaRecorder" in js


def test_app_js_calls_the_three_session_endpoints() -> None:
    js = _read("app.js")
    assert '"/api/transcribe"' in js
    assert '"/api/tutor"' in js
    assert '"/api/speak"' in js
