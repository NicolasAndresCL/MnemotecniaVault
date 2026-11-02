import pytest

from app import mnemonics as m


@pytest.mark.parametrize(
    ("word", "digits"),
    [
        ("gato", "71"),
        ("queso", "70"),
        ("cielo", "05"),
        ("llave", "69"),
        ("guitarra", "714"),
        ("yate", "61"),
        ("rey", "4"),
        ("niño", "22"),
        ("Árbol", "495"),
        ("taxi", "170"),
        ("hoja", "6"),
        ("chancho", "626"),
    ],
)
def test_sistema_mayor(word, digits):
    assert m.word_to_digits(word) == digits


def test_peg_words_sugiere_palabras_que_codifican_el_trozo():
    pegs = m.peg_words("7105")
    assert list(pegs) == ["71", "05"]
    assert "gato" in pegs["71"]
    assert all(m.word_to_digits(w) == "05" for w in pegs["05"])


def test_iniciales_y_frase():
    items = ["Abstracción", "Encapsulamiento", "Modularidad", "Jerarquía"]
    assert m.initials(items) == "AEMJ"
    phrase = m.acronym_phrase(items, seed=1)
    words = phrase.split()
    # La primera palabra lleva verbo detrás; las iniciales del resto calzan.
    assert [w[0].upper() for w in [words[0], *words[2:]]] == list("AEMJ")


def test_primeras_letras_y_chunking_y_cloze():
    assert m.first_letters("Revisar y actuar, bajo el mismo candado.") == "R y a, b e m c."
    assert m.chunk_digits("56912345678", 3) == "569 123 456 78"
    assert m.cloze("La ligadura dinámica ocurre en ejecución", "ligadura dinámica") == "La […] ocurre en ejecución"


def test_similitud_de_respuesta():
    assert m.answer_similarity("ligadura dinamica", "**Ligadura dinámica**") == 1.0
    assert m.answer_similarity("", "algo importante") == 0.0
    assert m.answer_similarity("x", "de la") == 1.0


@pytest.mark.parametrize("tech", list(m.TECHNIQUES))
def test_suggest_hook_para_cada_tecnica(tech):
    out = m.suggest_hook(tech, "¿Pilares de la POO?", "- Abstracción\n- Encapsulamiento\n- Puerto 5432", seed=3)
    assert out and "{" not in out


def test_suggest_hook_tecnica_desconocida():
    with pytest.raises(ValueError):
        m.suggest_hook("telepatia", "a", "b")


@pytest.mark.parametrize(
    ("kind", "back", "tech"),
    [
        ("tabla", "Puerto 5432", "sistema_mayor"),
        ("definicion", "- uno\n- dos\n- tres", "acronimo"),
        ("definicion", "1. uno\n2. dos\n3. tres", "historia"),
        ("comando", "docker ps -a", "imagen_absurda"),
        ("leccion", "No reescribir commits pusheados", "frase_ancla"),
        ("cloze", "Encapsulamiento", "rima"),
        ("resumen", "x" * 200, "imagen_absurda"),
    ],
)
def test_recomendar_tecnica(kind, back, tech):
    assert m.recommend_technique(kind, back) == tech
