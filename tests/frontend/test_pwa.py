import json
from pathlib import Path

FRONTEND_DIR = Path(__file__).resolve().parent.parent.parent / "frontend"


def _read(filename: str) -> str:
    return (FRONTEND_DIR / filename).read_text(encoding="utf-8")


def test_manifest_is_valid_json_with_required_fields() -> None:
    manifest = json.loads(_read("manifest.json"))

    assert manifest["name"] == "SpeakWise"
    assert manifest["short_name"] == "SpeakWise"
    assert manifest["start_url"] == "/"
    assert manifest["display"] == "standalone"


def test_manifest_has_192_and_512_icons_that_exist_on_disk() -> None:
    manifest = json.loads(_read("manifest.json"))
    sizes_present = {icon["sizes"] for icon in manifest["icons"]}

    assert "192x192" in sizes_present
    assert "512x512" in sizes_present
    for icon in manifest["icons"]:
        icon_path = FRONTEND_DIR / icon["src"]
        assert icon_path.is_file(), f"falta el archivo {icon['src']}"


def test_index_html_links_manifest() -> None:
    html = _read("index.html")
    assert '<link rel="manifest" href="manifest.json">' in html


def test_service_worker_has_fetch_listener() -> None:
    sw = _read("service-worker.js")
    assert "addEventListener(\"fetch\"" in sw or "addEventListener('fetch'" in sw


def test_service_worker_is_network_first_not_cache_first() -> None:
    """cache-first sirve HTML/JS viejo indefinidamente tras un deploy nuevo —
    bug real encontrado probando Fase 9 en vivo (el navegador mostraba la
    versión de Fase 8 aunque el servidor ya tenía la de Fase 9)."""
    sw = _read("service-worker.js")
    assert "fetch(event.request)" in sw
    fetch_block = sw.split('addEventListener("fetch"')[1]
    fetch_call_pos = fetch_block.index("fetch(event.request)")
    cache_match_pos = fetch_block.index("caches.match(event.request)")
    assert fetch_call_pos < cache_match_pos, "debe intentar red antes que cache"


def test_app_js_registers_service_worker() -> None:
    js = _read("app.js")
    assert "navigator.serviceWorker.register" in js
