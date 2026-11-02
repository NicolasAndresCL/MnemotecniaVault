from datetime import UTC, datetime, timedelta

import pytest

from app import srs
from app.errors import InvalidInput
from app.models import Card

NOW = datetime(2026, 11, 2, 12, 0, tzinfo=UTC)


def _card() -> Card:
    return Card(id=1, deck_id=1, key="k", kind="manual", front="f", back="b", state=0, due=NOW, reps=0, lapses=0)


def test_nueva_bien_pasa_a_aprendiendo_con_pasos_de_minutos():
    card = _card()
    review = srs.apply_review(card, 3, now=NOW)
    assert card.state == 1 and card.reps == 1
    assert review.state_before == srs.NEW
    assert timedelta(minutes=5) < card.due - NOW < timedelta(hours=1)


def test_facil_programa_mas_lejos_que_dificil():
    p = srs.preview(_card(), now=NOW)
    assert p[1] <= p[2] <= p[3] < p[4]


def test_olvidar_en_repaso_cuenta_lapso():
    card = _card()
    srs.apply_review(card, 4, now=NOW)  # Fácil: directo a repaso
    assert card.state == 2
    later = card.due
    srs.apply_review(card, 1, now=later)
    assert card.lapses == 1 and card.state == 3


def test_retrievability_baja_con_el_tiempo():
    card = _card()
    assert srs.retrievability(card, now=NOW) is None
    srs.apply_review(card, 4, now=NOW)
    r1 = srs.retrievability(card, now=NOW + timedelta(days=1))
    r2 = srs.retrievability(card, now=NOW + timedelta(days=60))
    assert 0 < r2 < r1 <= 1


def test_calificacion_invalida():
    with pytest.raises(InvalidInput):
        srs.apply_review(_card(), 7, now=NOW)


def test_retencion_fuera_de_rango():
    with pytest.raises(InvalidInput):
        srs.scheduler(0.5)


@pytest.mark.parametrize(
    ("td", "txt"),
    [
        (timedelta(seconds=30), "1 min"),
        (timedelta(minutes=10), "10 min"),
        (timedelta(hours=5), "5 h"),
        (timedelta(days=3), "3 d"),
        (timedelta(days=90), "3,0 m"),
        (timedelta(days=800), "2,2 a"),
    ],
)
def test_format_interval(td, txt):
    assert srs.format_interval(td) == txt
