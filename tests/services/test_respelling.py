from backend.services.phoneme import simple_respelling


def test_simple_respelling_monosyllabic_word_no_caps() -> None:
    """Ejemplo exacto del usuario: "book" -> "buk", sin mayúsculas porque
    en una sola sílaba no hay contraste de acento que marcar."""
    assert simple_respelling("book") == "buk"


def test_simple_respelling_marks_stressed_syllable_uppercase() -> None:
    assert simple_respelling("average") == "A-ver-ij"


def test_simple_respelling_stress_on_second_syllable() -> None:
    assert simple_respelling("about") == "uh-BOWT"


def test_simple_respelling_three_syllables() -> None:
    assert simple_respelling("banana") == "buh-NA-nuh"


def test_simple_respelling_unknown_word_returns_none() -> None:
    assert simple_respelling("zzznotaword") is None
