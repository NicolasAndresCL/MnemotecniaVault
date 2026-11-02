"""Repaso espaciado con FSRS (Free Spaced Repetition Scheduler, el algoritmo por defecto de Anki desde 23.10).

FSRS modela cada recuerdo con tres variables (modelo DSR):
- **Estabilidad (S)**: días que tarda la probabilidad de recordar en caer al 90 %.
- **Dificultad (D)**: 1–10, cuánto cuesta subir la estabilidad de esa tarjeta.
- **Recuperabilidad (R)**: probabilidad de recordarla *hoy*; decae con el tiempo según S.

Programa el próximo repaso justo cuando R baja a la retención deseada (0,9 por defecto): repasar antes
desperdicia tiempo y repasar después cuesta un olvido. Este módulo traduce entre `models.Card` y `fsrs.Card`.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from functools import lru_cache

from fsrs import Card as FCard
from fsrs import Rating, Scheduler, State

from app.errors import InvalidInput
from app.models import Card, Review

NEW = 0  # estado propio: tarjeta que nunca se ha visto (fsrs no lo distingue de «aprendiendo»)

RATINGS: dict[int, tuple[str, str]] = {
    1: ("Otra vez", "negative"),
    2: ("Difícil", "warning"),
    3: ("Bien", "positive"),
    4: ("Fácil", "info"),
}

STATE_LABELS = {0: "Nueva", 1: "Aprendiendo", 2: "Repaso", 3: "Reaprendiendo"}


@lru_cache
def scheduler(desired_retention: float = 0.9, fuzz: bool = True) -> Scheduler:
    if not 0.7 <= desired_retention <= 0.99:
        raise InvalidInput("La retención deseada debe estar entre 0,70 y 0,99")
    # Fuzz: reparte unos días los vencimientos para que no se amontonen las tarjetas creadas juntas.
    return Scheduler(desired_retention=desired_retention, enable_fuzzing=fuzz)


def to_fsrs(card: Card) -> FCard:
    if card.state == NEW:
        return FCard(card_id=card.id or 0, due=card.due)
    return FCard(
        card_id=card.id or 0,
        state=State(card.state),
        step=card.step,
        stability=card.stability,
        difficulty=card.difficulty,
        due=card.due,
        last_review=card.last_review,
    )


def apply_review(
    card: Card,
    rating: int,
    *,
    now: datetime | None = None,
    duration_ms: int | None = None,
    typed_answer: str | None = None,
    desired_retention: float = 0.9,
) -> Review:
    """Registra una respuesta: actualiza el estado FSRS de `card` y devuelve el `Review` (sin persistir)."""
    if rating not in RATINGS:
        raise InvalidInput(f"Calificación inválida: {rating} (1–4)")
    now = now or datetime.now(UTC)
    before = card.state
    fcard, _log = scheduler(desired_retention).review_card(to_fsrs(card), Rating(rating), review_datetime=now)

    card.state = int(fcard.state)
    card.step = fcard.step
    card.stability = fcard.stability
    card.difficulty = fcard.difficulty
    card.due = fcard.due
    card.last_review = fcard.last_review
    card.reps += 1
    # Lapso = se olvidó algo que ya estaba consolidado (en repaso), no un tropiezo mientras se aprende.
    if rating == 1 and before == int(State.Review):
        card.lapses += 1

    return Review(
        card_id=card.id,
        rating=rating,
        reviewed_at=now,
        duration_ms=duration_ms,
        state_before=before,
        stability_after=card.stability,
        difficulty_after=card.difficulty,
        due_after=card.due,
        typed_answer=typed_answer,
    )


def preview(card: Card, *, now: datetime | None = None, desired_retention: float = 0.9) -> dict[int, timedelta]:
    """Intervalo que daría cada botón (sin fuzz, para que la etiqueta no baile)."""
    now = now or datetime.now(UTC)
    sch = scheduler(desired_retention, fuzz=False)
    base = to_fsrs(card)
    return {r: sch.review_card(base, Rating(r), review_datetime=now)[0].due - now for r in RATINGS}


def retrievability(card: Card, *, now: datetime | None = None, desired_retention: float = 0.9) -> float | None:
    """Probabilidad estimada de recordar la tarjeta ahora (None si nunca se repasó)."""
    if card.state == NEW or card.last_review is None:
        return None
    return float(scheduler(desired_retention).get_card_retrievability(to_fsrs(card), current_datetime=now))


def format_interval(td: timedelta) -> str:
    secs = max(0, int(td.total_seconds()))
    if secs < 3600:
        return f"{max(1, round(secs / 60))} min"
    if secs < 86400:
        return f"{round(secs / 3600)} h"
    days = secs / 86400
    if days < 30:
        return f"{round(days)} d"
    if days < 365:
        return f"{days / 30:.1f} m".replace(".", ",")
    return f"{days / 365:.1f} a".replace(".", ",")
