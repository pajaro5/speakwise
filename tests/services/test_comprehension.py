import pytest

from backend.services.comprehension import estimate_comprehensibility


def test_estimate_comprehensibility_perfect_conditions() -> None:
    assert estimate_comprehensibility(wpm=120, fillers=0, word_count=20) == 5.0


def test_estimate_comprehensibility_penalizes_high_filler_ratio() -> None:
    """25% de las palabras son fillers (um, uh, ...) -> penaliza bastante,
    pero wpm ideal no penaliza nada."""
    score = estimate_comprehensibility(wpm=120, fillers=5, word_count=20)
    assert score == pytest.approx(3.0)


def test_estimate_comprehensibility_penalizes_too_slow() -> None:
    """Reportado como hipótesis de diseño, no del usuario: hablar muy
    lento suele indicar que el alumno está construyendo la oración
    palabra por palabra, no fluidez real."""
    score = estimate_comprehensibility(wpm=30, fillers=0, word_count=10)
    assert score < 5.0


def test_estimate_comprehensibility_penalizes_too_fast() -> None:
    score = estimate_comprehensibility(wpm=300, fillers=0, word_count=30)
    assert score < 5.0


def test_estimate_comprehensibility_clamps_at_one() -> None:
    score = estimate_comprehensibility(wpm=500, fillers=15, word_count=20)
    assert score == 1.0


def test_estimate_comprehensibility_returns_none_without_evidence() -> None:
    """Sin palabras transcritas (ej. silencio, o audio no reconocido) no
    hay evidencia real de comprensibilidad -- no se inventa un 5.0 ni un
    1.0, se deja sin dato (igual que pattern_progress/user_progress: sin
    señal real, no se actualiza nada)."""
    assert estimate_comprehensibility(wpm=0, fillers=0, word_count=0) is None
