from datetime import date, timedelta

# Intervalo (días) hasta el próximo repaso, según exposiciones acumuladas —
# variante simplificada de SM-2 (DESIGN.md la nombra como spaced_rep.py):
# sin una calificación de calidad 0-5 (no la tenemos, solo la señal binaria
# "la palabra apareció en conversación libre"), se usa crecimiento fijo en
# vez del ease factor completo de SM-2.
_INTERVALS_DAYS = [1, 3, 7, 14, 30]

# Cuánto sube el score en cada uso exitoso — llega a "dominado" (1.0) tras
# ~7 usos reales, sin inventar un score alto de un solo uso.
_SCORE_STEP = 0.15


def next_review_date(today: date, exposures: int) -> str:
    idx = min(max(exposures, 1) - 1, len(_INTERVALS_DAYS) - 1)
    return (today + timedelta(days=_INTERVALS_DAYS[idx])).isoformat()


def score_after_success(previous_score: float) -> float:
    return min(1.0, previous_score + _SCORE_STEP)
