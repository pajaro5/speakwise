from datetime import date

import pytest

from backend.services.spaced_rep import next_review_date, score_after_success


def test_next_review_date_first_exposure_is_tomorrow() -> None:
    assert next_review_date(date(2026, 8, 7), exposures=1) == "2026-08-08"


def test_next_review_date_grows_with_exposures() -> None:
    assert next_review_date(date(2026, 8, 7), exposures=2) == "2026-08-10"
    assert next_review_date(date(2026, 8, 7), exposures=3) == "2026-08-14"
    assert next_review_date(date(2026, 8, 7), exposures=4) == "2026-08-21"
    assert next_review_date(date(2026, 8, 7), exposures=5) == "2026-09-06"


def test_next_review_date_caps_at_max_interval() -> None:
    """No sigue creciendo indefinidamente más allá del intervalo máximo
    (30 días) — una vez ahí, se repasa cada 30 días."""
    assert next_review_date(date(2026, 8, 7), exposures=5) == next_review_date(
        date(2026, 8, 7), exposures=20
    )


def test_score_after_success_increases_score() -> None:
    assert score_after_success(0.0) == pytest.approx(0.15)


def test_score_after_success_caps_at_one() -> None:
    assert score_after_success(0.95) == pytest.approx(1.0)
