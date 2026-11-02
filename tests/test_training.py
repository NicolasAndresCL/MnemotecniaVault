import random

from app import training as t
from app.mnemonics import word_to_digits


def test_escalera_sube_y_baja():
    lv = t.Level(value=4)
    lv.record(True)
    assert lv.value == 5 and lv.best == 4
    lv.record(False)
    assert lv.value == 5
    lv.record(False)
    assert lv.value == 4
    assert lv.history == [True, False, False]


def test_escalera_respeta_limites():
    lv = t.Level(value=2, minimum=2)
    for _ in range(4):
        lv.record(False)
    assert lv.value == 2


def test_digitos():
    seq = t.digit_sequence(6, random.Random(1))
    assert len(seq) == 6 and seq.isdigit()
    assert t.check_digits(seq, " ".join(seq))
    assert not t.check_digits(seq, "0" * 7)


def test_sistema_mayor_reto_y_validacion():
    number, word = t.major_challenge(random.Random(2))
    assert word_to_digits(word) == number and len(number) == 2
    assert t.check_major_word(number, word)
    assert not t.check_major_word(number, "")


def test_pares():
    pairs = t.word_pairs(4, random.Random(3))
    assert len(pairs) == 4 and len({w for p in pairs for w in p}) == 8
    answers = {pairs[0][0]: pairs[0][1].upper(), pairs[1][0]: "nada"}
    assert t.score_pairs(pairs, answers) == 1
