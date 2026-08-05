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


def test_index_html_has_conversation_support_categories_in_module_3() -> None:
    """Panel de apoyo a la conversación libre — reportado por el usuario
    ("me quedo en blanco"). 3 categorías pedidas explícitamente: frases para
    iniciar, conectores de ideas, temas para conversar."""
    html = _read("index.html")
    for element_id in ["conversation-starters", "linking-words", "topic-suggestions"]:
        assert f'id="{element_id}"' in html, f"falta #{element_id}"


def test_app_js_gives_clear_recording_state_feedback() -> None:
    """El estado de grabación tiene que ser obvio — bug real reportado por el
    usuario ("el Grabar-parar no es intuitivo")."""
    js = _read("app.js")
    assert "disabled = true" in js
    assert "disabled = false" in js


def test_app_js_disables_listen_buttons_while_playing_audio() -> None:
    """El TTS real tarda un poco en generar el audio — el usuario reportó
    que sigue presionando "Escuchar ejemplos" varias veces porque no ve
    feedback de que ya está cargando."""
    js = _read("app.js")
    assert "btn.disabled = true" in js
    assert "playTextWithButton(todaysPlan.pattern_focus.family.join(\". \"), listenPatternBtn)" in js
    assert "playTextWithButton(todaysPlan.chunk_today.chunk, listenChunkBtn)" in js


def test_index_html_has_pattern_pronunciation_element() -> None:
    """El usuario pidió que se muestre cómo pronunciar el patrón (IPA), no
    solo la regla en español y los ejemplos para escuchar."""
    html = _read("index.html")
    assert 'id="pattern-ipa"' in html


def test_index_html_has_chunk_examples_elements() -> None:
    """El usuario pidió 3 ejemplos de uso del chunk del día: oración simple,
    párrafo, conversación."""
    html = _read("index.html")
    for element_id in [
        "chunk-examples-status", "chunk-example-sentence",
        "chunk-example-paragraph", "chunk-example-conversation",
    ]:
        assert f'id="{element_id}"' in html, f"falta #{element_id}"


def test_app_js_loads_chunk_examples_when_entering_module_2() -> None:
    js = _read("app.js")
    assert '"/api/chunk-examples"' in js


def test_index_html_chunk_examples_use_icons_not_spanish_labels() -> None:
    """El usuario pidió íconos en vez de texto para oración simple/párrafo/
    conversación."""
    html = _read("index.html")
    assert "✏️" in html
    assert "📄" in html
    assert "💬" in html
    assert "Oración simple:" not in html
    assert "Párrafo:" not in html
    assert "Conversación:" not in html


def test_index_html_chunk_text_is_always_bold() -> None:
    """El usuario pidió que el chunk del día siempre aparezca en negrita."""
    html = _read("index.html")
    assert '<strong id="chunk-text">' in html


def test_app_js_bolds_chunk_occurrences_inside_examples() -> None:
    """El chunk debe verse en negrita también dentro de los 3 ejemplos
    generados, no solo en el display principal."""
    js = _read("app.js")
    assert "boldChunkOccurrences" in js
    assert "chunkExampleSentenceEl.innerHTML" in js
    assert "chunkExampleParagraphEl.innerHTML" in js
    assert "chunkExampleConversationEl.innerHTML" in js


def test_app_js_bolding_ignores_trailing_punctuation() -> None:
    """Verificado en vivo: el LLM a veces sigue la oración después del chunk
    ("Be careful with that glass vase...") sin el punto final, y el match
    exacto fallaba en resaltarlo. Hay que ignorar puntuación final del chunk
    al buscar coincidencias."""
    js = _read("app.js")
    assert "[.!?]+$" in js


def test_ui_text_is_in_english_not_spanish() -> None:
    """El usuario pidió que toda la interfaz (botones, instrucciones,
    mensajes de estado/error) esté en inglés. Las explicaciones de reglas
    de pronunciación (rule_es, dato de la DB) quedan en español a propósito
    -- esto solo cubre el texto fijo de index.html/app.js."""
    html = _read("index.html")
    js = _read("app.js")
    spanish_markers = [
        "Empezar sesión", "Escuchar ejemplos", "Grabar mi intento", "Siguiente",
        "Módulo", "Pronunciación:", "Usarlo en una oración", "Conversación libre",
        "blanco", "arrancar", "Conectores", "Temas:",
        "Cargando el plan", "Grabando", "Transcribiendo", "Pensando",
        "Generando audio", "Listo.", "Practicado", "Usaste el chunk",
        "no detecté el chunk", "No se pudieron cargar", "Cargando ejemplos",
    ]
    for marker in spanish_markers:
        assert marker not in html, f"queda texto en español en index.html: {marker!r}"
        assert marker not in js, f"queda texto en español en app.js: {marker!r}"
