# DESIGN.md propone que Claude (el LLM tutor) evalúe comprehensibility en
# cada turno — eso implica una llamada/salida estructurada extra por turno
# solo para un número, con costo y latencia adicionales en un producto que
# ya es consciente del costo de API (API_COST_ALERT_USD). En su lugar, se
# deriva de señales objetivas que ya se calculan por turno (wpm, fillers,
# sin costo extra) — un proxy, no una medida real de si el interlocutor
# entendió, pero real y variable (a diferencia de quedar sin escribir
# nunca, que es el estado anterior: sessions.comprehensibility nunca se
# escribía y difficulty() se quedaba congelada en "maintain" para siempre).
IDEAL_WPM_LOW = 90
IDEAL_WPM_HIGH = 160
FILLER_PENALTY_WEIGHT = 8.0
WPM_PENALTY_WEIGHT = 3.0


def estimate_comprehensibility(
    *, wpm: float, fillers: int, word_count: int
) -> float | None:
    """Proxy de comprehensibility (1.0-5.0) a partir de wpm y proporción
    de fillers. None si no hay evidencia real (nada transcrito) — no se
    inventa un valor, mismo criterio que pattern_progress/user_progress."""
    if word_count <= 0:
        return None

    score = 5.0
    score -= (fillers / word_count) * FILLER_PENALTY_WEIGHT

    if wpm < IDEAL_WPM_LOW:
        score -= (IDEAL_WPM_LOW - wpm) / IDEAL_WPM_LOW * WPM_PENALTY_WEIGHT
    elif wpm > IDEAL_WPM_HIGH:
        score -= (wpm - IDEAL_WPM_HIGH) / IDEAL_WPM_HIGH * WPM_PENALTY_WEIGHT

    return max(1.0, min(5.0, round(score, 2)))
