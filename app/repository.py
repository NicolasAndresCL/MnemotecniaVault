"""Acceso a datos. **Todo el SQL vive aquí**: la UI y la API solo orquestan."""

from __future__ import annotations

import random
from collections import Counter
from collections.abc import Iterable
from datetime import UTC, date, datetime, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy import case, delete, func, or_, select, update
from sqlalchemy.orm import Session, selectinload

from app import srs
from app.config import get_settings
from app.errors import Conflict, InvalidInput, NotFound
from app.importers.base import CardDraft, slugify
from app.models import TECHNIQUES, Card, Deck, Hook, Locus, Palace, Review, TrainingResult, utcnow

MASTERED_DAYS = 21  # estabilidad ≥ 3 semanas = recuerdo consolidado (umbral usual de «madura» en Anki)


def _tz() -> ZoneInfo:
    return ZoneInfo(get_settings().timezone)


def local_day(dt: datetime) -> date:
    return dt.astimezone(_tz()).date()


def start_of_local_day(now: datetime) -> datetime:
    local = now.astimezone(_tz())
    return local.replace(hour=0, minute=0, second=0, microsecond=0).astimezone(UTC)


# --------------------------------------------------------------------------- mazos
def list_decks(s: Session, now: datetime | None = None) -> list[dict]:
    now = now or utcnow()
    active = Card.suspended.is_(False)
    rows = s.execute(
        select(
            Deck,
            func.count(Card.id),
            func.sum(case((active & (Card.state == srs.NEW), 1), else_=0)),
            func.sum(case((active & (Card.state != srs.NEW) & (Card.due <= now), 1), else_=0)),
            func.sum(case((active & (Card.stability >= MASTERED_DAYS), 1), else_=0)),
            func.sum(case((Card.suspended.is_(True), 1), else_=0)),
        )
        .outerjoin(Card, Card.deck_id == Deck.id)
        .group_by(Deck.id)
        .order_by(Deck.source, Deck.name)
    ).all()
    out = []
    for deck, total, new, due, mastered, suspended in rows:
        total = total or 0
        active_total = total - (suspended or 0)
        out.append(
            {
                "id": deck.id,
                "slug": deck.slug,
                "name": deck.name,
                "source": deck.source,
                "description": deck.description,
                "total": total,
                "new": new or 0,
                "due": due or 0,
                "mastered": mastered or 0,
                "suspended": suspended or 0,
                "mastery": round(100 * (mastered or 0) / active_total) if active_total else 0,
            }
        )
    return out


def get_deck(s: Session, deck_id: int) -> Deck:
    deck = s.get(Deck, deck_id)
    if deck is None:
        raise NotFound(f"No existe el mazo {deck_id}")
    return deck


def create_deck(s: Session, name: str, description: str = "") -> Deck:
    name = name.strip()
    if not name:
        raise InvalidInput("El mazo necesita un nombre")
    slug = "manual-" + slugify(name)
    if s.scalar(select(Deck.id).where(Deck.slug == slug)):
        raise Conflict(f"Ya existe un mazo «{name}»")
    deck = Deck(slug=slug, name=name, source="manual", description=description)
    s.add(deck)
    s.flush()
    return deck


def _deck_for(s: Session, cache: dict[str, Deck], draft: CardDraft) -> Deck:
    deck = cache.get(draft.deck_slug)
    if deck is None:
        deck = s.scalar(select(Deck).where(Deck.slug == draft.deck_slug))
        if deck is None:
            deck = Deck(slug=draft.deck_slug, name=draft.deck_name, source=draft.deck_source)
            s.add(deck)
            s.flush()
        elif deck.name != draft.deck_name:
            deck.name = draft.deck_name
        cache[draft.deck_slug] = deck
    return deck


def upsert_drafts(s: Session, drafts: Iterable[CardDraft], source: str) -> dict[str, int]:
    """Sincroniza las tarjetas de una fuente sin perder el progreso.

    - Nueva clave → tarjeta nueva. Clave existente con otro texto → se actualiza el texto, no el FSRS.
    - Tarjetas importadas de esa fuente que ya no vienen → `orphan` + `suspended` (el historial queda).
    """
    stats = Counter(created=0, updated=0, unchanged=0, orphaned=0, restored=0)
    decks: dict[str, Deck] = {}
    seen: dict[int, set[str]] = {}
    for d in drafts:
        deck = _deck_for(s, decks, d)
        keys = seen.setdefault(deck.id, set())
        if d.key in keys:
            continue
        keys.add(d.key)
        card = s.scalar(select(Card).where(Card.deck_id == deck.id, Card.key == d.key))
        if card is None:
            s.add(
                Card(
                    deck_id=deck.id,
                    key=d.key,
                    kind=d.kind,
                    front=d.front,
                    back=d.back,
                    context=d.context,
                    tags=list(d.tags),
                )
            )
            stats["created"] += 1
            continue
        if card.orphan:
            card.orphan = False
            card.suspended = False
            stats["restored"] += 1
        if (card.front, card.back, card.context, card.kind) != (d.front, d.back, d.context, d.kind):
            card.front, card.back, card.context, card.kind, card.tags = d.front, d.back, d.context, d.kind, list(d.tags)
            stats["updated"] += 1
        else:
            stats["unchanged"] += 1
    s.flush()

    source_decks = s.scalars(select(Deck).where(Deck.source == source)).all()
    for deck in source_decks:
        keys = seen.get(deck.id, set())
        q = update(Card).where(Card.deck_id == deck.id, Card.origin == "import", Card.orphan.is_(False))
        if keys:
            q = q.where(Card.key.not_in(keys))
        res = s.execute(q.values(orphan=True, suspended=True).execution_options(synchronize_session=False))
        stats["orphaned"] += res.rowcount or 0
    s.expire_all()
    return dict(stats)


# --------------------------------------------------------------------------- tarjetas
def get_card(s: Session, card_id: int) -> Card:
    card = s.scalar(select(Card).options(selectinload(Card.hooks), selectinload(Card.deck)).where(Card.id == card_id))
    if card is None:
        raise NotFound(f"No existe la tarjeta {card_id}")
    return card


def search_cards(
    s: Session,
    q: str = "",
    deck_id: int | None = None,
    kind: str | None = None,
    include_suspended: bool = False,
    limit: int = 100,
) -> list[Card]:
    stmt = select(Card).options(selectinload(Card.deck), selectinload(Card.hooks))
    if deck_id:
        stmt = stmt.where(Card.deck_id == deck_id)
    if kind:
        stmt = stmt.where(Card.kind == kind)
    if not include_suspended:
        stmt = stmt.where(Card.suspended.is_(False))
    for term in q.split():
        like = f"%{term}%"
        stmt = stmt.where(or_(Card.front.ilike(like), Card.back.ilike(like), Card.context.ilike(like)))
    return list(s.scalars(stmt.order_by(Card.deck_id, Card.id).limit(limit)))


def create_card(s: Session, deck_id: int, front: str, back: str, kind: str = "manual", context: str = "") -> Card:
    get_deck(s, deck_id)
    if not front.strip() or not back.strip():
        raise InvalidInput("La tarjeta necesita pregunta y respuesta")
    card = Card(
        deck_id=deck_id,
        key="manual-" + utcnow().strftime("%Y%m%d%H%M%S%f"),
        kind=kind,
        front=front.strip(),
        back=back.strip(),
        context=context,
        origin="manual",
    )
    s.add(card)
    s.flush()
    return card


def update_card(s: Session, card_id: int, front: str, back: str) -> Card:
    card = get_card(s, card_id)
    if card.origin == "import":
        raise Conflict("Las tarjetas importadas se corrigen en su fuente (la nota) y se reimportan")
    card.front, card.back = front.strip(), back.strip()
    return card


def set_suspended(s: Session, card_id: int, suspended: bool) -> Card:
    card = get_card(s, card_id)
    card.suspended = suspended
    return card


def delete_card(s: Session, card_id: int) -> None:
    card = get_card(s, card_id)
    if card.origin == "import":
        raise Conflict("Una tarjeta importada no se borra: suspéndela (volvería en la próxima importación)")
    s.delete(card)


# --------------------------------------------------------------------------- cola de repaso
def _today(now: datetime):
    start = start_of_local_day(now)
    return (Review.reviewed_at >= start) & (Review.reviewed_at < start + timedelta(days=1))


def new_introduced_today(s: Session, now: datetime) -> int:
    return s.scalar(select(func.count(Review.id)).where(_today(now), Review.state_before == srs.NEW)) or 0


def review_queue(
    s: Session,
    *,
    deck_ids: list[int] | None = None,
    now: datetime | None = None,
    new_limit: int | None = None,
    limit: int | None = None,
    seed: int | None = None,
) -> list[Card]:
    """Cola del día con **práctica intercalada**: mezcla mazos y tipos en vez de repasar en bloque.

    Orden: primero lo que está aprendiéndose (pasos de minutos), después repasos vencidos y nuevas
    mezclados. Las nuevas se sortean entre los mazos elegidos (si no, saldría siempre el primero) y
    respetan el cupo diario para no hipotecar los días siguientes.
    """
    cfg = get_settings()
    now = now or utcnow()
    limit = limit or cfg.max_reviews_per_session
    new_left = max(0, (cfg.new_per_day if new_limit is None else new_limit) - new_introduced_today(s, now))
    base = select(Card).options(selectinload(Card.hooks), selectinload(Card.deck)).where(Card.suspended.is_(False))
    if deck_ids:
        base = base.where(Card.deck_id.in_(deck_ids))

    learning = list(s.scalars(base.where(Card.state.in_((1, 3)), Card.due <= now).order_by(Card.due)))
    reviews = list(s.scalars(base.where(Card.state == 2, Card.due <= now).order_by(Card.due).limit(limit)))
    news = (
        list(s.scalars(base.where(Card.state == srs.NEW).order_by(func.random()).limit(new_left))) if new_left else []
    )

    rng = random.Random(seed)
    mixed = reviews + news
    rng.shuffle(mixed)
    return (learning + mixed)[:limit]


def record_review(
    s: Session,
    card_id: int,
    rating: int,
    *,
    now: datetime | None = None,
    duration_ms: int | None = None,
    typed_answer: str | None = None,
) -> Card:
    card = get_card(s, card_id)
    review = srs.apply_review(
        card,
        rating,
        now=now,
        duration_ms=duration_ms,
        typed_answer=typed_answer,
        desired_retention=get_settings().desired_retention,
    )
    s.add(review)
    s.flush()
    return card


# --------------------------------------------------------------------------- ganchos
def add_hook(s: Session, card_id: int, technique: str, text: str) -> Hook:
    if technique not in TECHNIQUES:
        raise InvalidInput(f"Técnica desconocida: {technique}")
    if not text.strip():
        raise InvalidInput("El gancho está vacío")
    get_card(s, card_id)
    hook = Hook(card_id=card_id, technique=technique, text=text.strip())
    s.add(hook)
    s.flush()
    return hook


def delete_hook(s: Session, hook_id: int) -> None:
    s.execute(delete(Hook).where(Hook.id == hook_id))


def list_hooks(s: Session, limit: int = 200) -> list[Hook]:
    return list(
        s.scalars(
            select(Hook)
            .options(selectinload(Hook.card).selectinload(Card.deck))
            .order_by(Hook.created_at.desc())
            .limit(limit)
        )
    )


# --------------------------------------------------------------------------- palacios
def list_palaces(s: Session) -> list[Palace]:
    return list(s.scalars(select(Palace).options(selectinload(Palace.loci)).order_by(Palace.name)))


def get_palace(s: Session, palace_id: int) -> Palace:
    palace = s.scalar(
        select(Palace)
        .options(selectinload(Palace.loci).selectinload(Locus.card).selectinload(Card.deck))
        .where(Palace.id == palace_id)
    )
    if palace is None:
        raise NotFound(f"No existe el palacio {palace_id}")
    return palace


def create_palace(s: Session, name: str, stations: list[str], description: str = "") -> Palace:
    name = name.strip()
    stations = [st.strip() for st in stations if st.strip()]
    if not name or not stations:
        raise InvalidInput("El palacio necesita nombre y al menos una estación")
    if s.scalar(select(Palace.id).where(Palace.name == name)):
        raise Conflict(f"Ya existe el palacio «{name}»")
    palace = Palace(name=name, description=description)
    palace.loci = [Locus(position=i, place=st) for i, st in enumerate(stations, start=1)]
    s.add(palace)
    s.flush()
    return palace


def update_locus(s: Session, locus_id: int, *, scene: str | None = None, card_id: int | None | bool = False) -> Locus:
    locus = s.get(Locus, locus_id)
    if locus is None:
        raise NotFound(f"No existe la estación {locus_id}")
    if scene is not None:
        locus.scene = scene.strip()
    if card_id is not False:  # False = no tocar; None = desanclar
        if card_id is not None:
            get_card(s, int(card_id))
        locus.card_id = card_id  # type: ignore[assignment]
    return locus


def delete_palace(s: Session, palace_id: int) -> None:
    s.delete(get_palace(s, palace_id))


# --------------------------------------------------------------------------- gimnasio
def save_training(s: Session, game: str, score: int, level: int, details: dict | None = None) -> TrainingResult:
    result = TrainingResult(game=game, score=score, level=level, details=details or {})
    s.add(result)
    s.flush()
    return result


def training_bests(s: Session) -> dict[str, dict]:
    rows = s.execute(
        select(TrainingResult.game, func.max(TrainingResult.score), func.count(TrainingResult.id)).group_by(
            TrainingResult.game
        )
    ).all()
    return {game: {"best": best, "played": played} for game, best, played in rows}


# --------------------------------------------------------------------------- estadísticas
def _activity_days(s: Session, since: datetime) -> Counter[date]:
    days: Counter[date] = Counter()
    for (ts,) in s.execute(select(Review.reviewed_at).where(Review.reviewed_at >= since)):
        days[local_day(ts)] += 1
    for (ts,) in s.execute(select(TrainingResult.played_at).where(TrainingResult.played_at >= since)):
        days[local_day(ts)] += 1
    return days


def streak(days: Counter[date], today: date) -> int:
    """Días seguidos con actividad. Si hoy aún no hay, la racha de ayer sigue viva."""
    current = today if days.get(today) else today - timedelta(days=1)
    n = 0
    while days.get(current):
        n += 1
        current -= timedelta(days=1)
    return n


def overview(s: Session, now: datetime | None = None) -> dict:
    now = now or utcnow()
    today = local_day(now)
    active = Card.suspended.is_(False)
    total, new, due, mastered = s.execute(
        select(
            func.count(Card.id),
            func.sum(case((Card.state == srs.NEW, 1), else_=0)),
            func.sum(case(((Card.state != srs.NEW) & (Card.due <= now), 1), else_=0)),
            func.sum(case((Card.stability >= MASTERED_DAYS, 1), else_=0)),
        ).where(active)
    ).one()
    reviewed_today = s.scalar(select(func.count(Review.id)).where(_today(now))) or 0

    month_ago = now - timedelta(days=30)
    mature = s.execute(
        select(func.count(Review.id), func.sum(case((Review.rating > 1, 1), else_=0))).where(
            Review.reviewed_at >= month_ago, Review.state_before == 2
        )
    ).one()
    retention = round(100 * (mature[1] or 0) / mature[0]) if mature[0] else None

    days = _activity_days(s, now - timedelta(days=370))
    new_left = max(0, get_settings().new_per_day - new_introduced_today(s, now))
    return {
        "total": total or 0,
        "new": new or 0,
        "due": due or 0,
        "mastered": mastered or 0,
        "reviewed_today": reviewed_today,
        "new_left_today": min(new_left, new or 0),
        "retention_30d": retention,
        "streak": streak(days, today),
        "active_days": len(days),
        "heatmap": {d.isoformat(): n for d, n in sorted(days.items())},
    }


def forecast(s: Session, now: datetime | None = None, days: int = 30) -> list[tuple[str, int]]:
    """Tarjetas que vencen cada día de los próximos `days` (carga futura de repaso)."""
    now = now or utcnow()
    until = now + timedelta(days=days)
    counts: Counter[date] = Counter()
    for (due,) in s.execute(
        select(Card.due).where(Card.suspended.is_(False), Card.state != srs.NEW, Card.due <= until)
    ):
        counts[max(local_day(due), local_day(now))] += 1
    start = local_day(now)
    return [((start + timedelta(days=i)).isoformat(), counts.get(start + timedelta(days=i), 0)) for i in range(days)]


def rating_breakdown(s: Session, now: datetime | None = None, days: int = 30) -> dict[int, int]:
    now = now or utcnow()
    rows = s.execute(
        select(Review.rating, func.count(Review.id))
        .where(Review.reviewed_at >= now - timedelta(days=days))
        .group_by(Review.rating)
    ).all()
    return {r: 0 for r in srs.RATINGS} | {int(r): n for r, n in rows}


def hardest_cards(s: Session, limit: int = 10) -> list[Card]:
    """Las que más se olvidan: candidatas a un gancho nuevo (o a reescribirse)."""
    return list(
        s.scalars(
            select(Card)
            .options(selectinload(Card.deck), selectinload(Card.hooks))
            .where(Card.suspended.is_(False), Card.lapses > 0)
            .order_by(Card.lapses.desc(), Card.difficulty.desc())
            .limit(limit)
        )
    )
