from collections import Counter
from datetime import UTC, date, datetime, timedelta

import pytest

from app import repository as repo
from app.errors import Conflict, InvalidInput, NotFound
from app.importers.base import CardDraft
from app.models import Card

NOW = datetime(2026, 11, 2, 15, 0, tzinfo=UTC)


def _draft(key: str, front: str = "¿Q?", back: str = "R", deck: str = "obsidian-cmdvault") -> CardDraft:
    return CardDraft(deck, "CmdVault", "obsidian", key, "definicion", front, back, "README.md", ("x",))


def test_upsert_crea_actualiza_y_conserva_progreso(db):
    st = repo.upsert_drafts(db, [_draft("a"), _draft("b"), _draft("b")], "obsidian")
    assert st["created"] == 2
    card = db.query(Card).filter_by(key="a").one()
    repo.record_review(db, card.id, 3, now=NOW)
    reps = card.reps

    st = repo.upsert_drafts(db, [_draft("a", back="R corregida"), _draft("b")], "obsidian")
    assert st["updated"] == 1 and st["unchanged"] == 1
    card = repo.get_card(db, card.id)
    assert card.back == "R corregida" and card.reps == reps  # el texto cambia, el progreso no


def test_upsert_huerfanas_y_restauradas(db):
    repo.upsert_drafts(db, [_draft("a"), _draft("b")], "obsidian")
    st = repo.upsert_drafts(db, [_draft("a")], "obsidian")
    assert st["orphaned"] == 1
    b = db.query(Card).filter_by(key="b").one()
    assert b.orphan and b.suspended
    st = repo.upsert_drafts(db, [_draft("a"), _draft("b")], "obsidian")
    assert st["restored"] == 1
    # Fuente vacía: todas huérfanas
    st = repo.upsert_drafts(db, [], "obsidian")
    assert st["orphaned"] == 2


def test_mazos_con_estadisticas(db):
    repo.upsert_drafts(db, [_draft("a"), _draft("b")], "obsidian")
    decks = repo.list_decks(db, NOW)
    assert decks[0]["total"] == 2 and decks[0]["new"] == 2 and decks[0]["mastery"] == 0
    with pytest.raises(NotFound):
        repo.get_deck(db, 999)


def test_mazo_y_tarjeta_manual(db):
    deck = repo.create_deck(db, "Diseño de Software")
    with pytest.raises(Conflict):
        repo.create_deck(db, "Diseño de Software")
    with pytest.raises(InvalidInput):
        repo.create_deck(db, "  ")
    card = repo.create_card(db, deck.id, "¿Pilares POO?", "AEMJ")
    with pytest.raises(InvalidInput):
        repo.create_card(db, deck.id, "", "x")
    card = repo.update_card(db, card.id, "¿Pilares de la POO?", "A-E-M-J")
    assert card.front == "¿Pilares de la POO?"
    repo.set_suspended(db, card.id, True)
    assert repo.search_cards(db, "Pilares") == []
    assert len(repo.search_cards(db, "Pilares", include_suspended=True, deck_id=deck.id, kind="manual")) == 1
    repo.delete_card(db, card.id)
    with pytest.raises(NotFound):
        repo.get_card(db, card.id)


def test_importadas_no_se_editan_ni_borran(db):
    repo.upsert_drafts(db, [_draft("a")], "obsidian")
    card = db.query(Card).filter_by(key="a").one()
    with pytest.raises(Conflict):
        repo.update_card(db, card.id, "x", "y")
    with pytest.raises(Conflict):
        repo.delete_card(db, card.id)


def test_cola_respeta_cupo_de_nuevas_e_intercala(db):
    repo.upsert_drafts(db, [_draft(str(i)) for i in range(30)], "obsidian")
    queue = repo.review_queue(db, now=NOW, new_limit=5, seed=1)
    assert len(queue) == 5
    repo.record_review(db, queue[0].id, 3, now=NOW)  # nueva → aprendiendo (consume cupo)
    later = NOW + timedelta(hours=1)
    queue = repo.review_queue(db, now=later, new_limit=5, seed=1)
    assert queue[0].state == 1  # lo que se está aprendiendo va primero
    assert sum(1 for c in queue if c.state == 0) == 4


def test_overview_racha_y_retencion(db):
    repo.upsert_drafts(db, [_draft(str(i)) for i in range(3)], "obsidian")
    cards = db.query(Card).all()
    for offset in (0, 1, 2):  # tres días seguidos
        repo.record_review(db, cards[offset].id, 4, now=NOW - timedelta(days=offset))
    repo.record_review(db, cards[0].id, 1, now=NOW + timedelta(days=30))  # lapso en repaso
    ov = repo.overview(db, now=NOW + timedelta(days=30))
    assert ov["total"] == 3 and ov["streak"] == 1
    assert ov["retention_30d"] == 0
    ov = repo.overview(db, now=NOW)
    assert ov["streak"] == 3 and ov["reviewed_today"] == 1
    assert len(repo.forecast(db, now=NOW, days=10)) == 10
    assert repo.rating_breakdown(db, now=NOW)[4] == 3
    assert repo.hardest_cards(db) == [] or repo.hardest_cards(db)[0].lapses >= 1


def test_streak_puro():
    today = date(2026, 11, 2)
    days = Counter({today - timedelta(days=1): 2, today - timedelta(days=2): 1})
    assert repo.streak(days, today) == 2  # hoy sin actividad aún: la racha de ayer sigue viva
    assert repo.streak(Counter(), today) == 0


def test_ganchos(db):
    repo.upsert_drafts(db, [_draft("a")], "obsidian")
    card = db.query(Card).one()
    hook = repo.add_hook(db, card.id, "rima", "Lo que importa, según quién lo porta")
    with pytest.raises(InvalidInput):
        repo.add_hook(db, card.id, "telepatia", "x")
    with pytest.raises(InvalidInput):
        repo.add_hook(db, card.id, "rima", " ")
    assert repo.list_hooks(db)[0].card.deck.name == "CmdVault"
    repo.delete_hook(db, hook.id)
    assert repo.list_hooks(db) == []


def test_palacios(db):
    repo.upsert_drafts(db, [_draft("a")], "obsidian")
    card = db.query(Card).one()
    palace = repo.create_palace(db, "Mi casa", ["Puerta", "Cocina", " "])
    assert [lc.position for lc in palace.loci] == [1, 2]
    with pytest.raises(Conflict):
        repo.create_palace(db, "Mi casa", ["x"])
    with pytest.raises(InvalidInput):
        repo.create_palace(db, "Vacío", [])
    locus = repo.update_locus(db, palace.loci[0].id, scene="Un titán abre la puerta", card_id=card.id)
    assert locus.card_id == card.id
    repo.update_locus(db, locus.id, card_id=None)
    assert repo.get_palace(db, palace.id).loci[0].card_id is None
    with pytest.raises(NotFound):
        repo.update_locus(db, 999, scene="x")
    assert len(repo.list_palaces(db)) == 1
    repo.delete_palace(db, palace.id)
    with pytest.raises(NotFound):
        repo.get_palace(db, palace.id)


def test_gimnasio(db):
    repo.save_training(db, "digitos", 7, 7, {"seq": "1234567"})
    repo.save_training(db, "digitos", 9, 9)
    assert repo.training_bests(db) == {"digitos": {"best": 9, "played": 2}}
