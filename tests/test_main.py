from fastapi.testclient import TestClient

from backend.main import app


def test_static_files_are_served_with_no_cache_header() -> None:
    """Encontrado probando en vivo: el navegador puede servir app.js viejo
    desde su caché HTTP normal después de un deploy, incluso con una
    recarga simple (no hace falta hard-refresh para notarlo) — distinto del
    problema de caché del service worker (Fase 8 de planVersion1.md, ya
    resuelto). Sin este header, el navegador puede saltarse la revalidación
    por completo según su heurística de frescura."""
    client = TestClient(app)

    response = client.get("/app.js")

    assert response.status_code == 200
    assert response.headers["cache-control"] == "no-cache"
