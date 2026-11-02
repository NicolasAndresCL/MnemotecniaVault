"""Modelo de datos.

Deck ─< Card ─< Review          (repaso espaciado)
           └─< Hook             (ganchos mnemotécnicos de la tarjeta)
Palace ─< Locus >─ Card         (palacio de la memoria: estaciones que anclan tarjetas)
TrainingResult                  (gimnasio: juegos de memoria de trabajo)
"""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    TypeDecorator,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


def utcnow() -> datetime:
    return datetime.now(UTC)


class UTCDateTime(TypeDecorator):
    """DateTime siempre con zona UTC. SQLite pierde la zona al guardar: se la devuelve al leer."""

    impl = DateTime(timezone=True)
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is not None and value.tzinfo is None:
            value = value.replace(tzinfo=UTC)
        return value

    def process_result_value(self, value, dialect):
        if value is not None and value.tzinfo is None:
            value = value.replace(tzinfo=UTC)
        return value


# Técnicas mnemotécnicas (skill `mnemotecnia`): clave → (nombre, para qué dato sirve).
TECHNIQUES: dict[str, tuple[str, str]] = {
    "acronimo": ("Acrónimo", "Lista cerrada que se pide completa"),
    "frase_ancla": ("Frase-ancla", "Regla de decisión"),
    "rima": ("Rima", "Definición breve"),
    "imagen_absurda": ("Imagen absurda", "Concepto abstracto"),
    "contraste_espejo": ("Contraste en espejo", "Par que se confunde"),
    "asociacion_forma": ("Asociación forma → significado", "Notación o símbolos"),
    "palacio": ("Palacio de la memoria", "Temario completo y en orden"),
    "sistema_mayor": ("Sistema mayor", "Números, puertos, versiones, fechas"),
    "historia": ("Cadena / historia", "Secuencia de pasos"),
}


class Deck(Base):
    __tablename__ = "decks"

    id: Mapped[int] = mapped_column(primary_key=True)
    slug: Mapped[str] = mapped_column(String(160), unique=True)
    name: Mapped[str] = mapped_column(String(200))
    source: Mapped[str] = mapped_column(String(20), default="manual")  # obsidian|cmdvault|proyecto|manual
    description: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)

    cards: Mapped[list[Card]] = relationship(back_populates="deck", cascade="all, delete-orphan")


class Card(Base):
    __tablename__ = "cards"
    __table_args__ = (
        UniqueConstraint("deck_id", "key", name="uq_card_deck_key"),
        Index("ix_cards_due", "suspended", "due"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    deck_id: Mapped[int] = mapped_column(ForeignKey("decks.id", ondelete="CASCADE"), index=True)
    key: Mapped[str] = mapped_column(String(64))
    kind: Mapped[str] = mapped_column(String(20))
    front: Mapped[str] = mapped_column(Text)
    back: Mapped[str] = mapped_column(Text)
    context: Mapped[str] = mapped_column(Text, default="")
    tags: Mapped[list[str]] = mapped_column(JSON, default=list)
    origin: Mapped[str] = mapped_column(String(10), default="import")  # import|manual
    # Suspendida: no aparece en el repaso (la fuente la borró o el usuario la apartó).
    suspended: Mapped[bool] = mapped_column(Boolean, default=False)
    orphan: Mapped[bool] = mapped_column(Boolean, default=False)  # ya no existe en la fuente

    # Estado FSRS (espejo de fsrs.Card). state: 0 = nueva (nunca vista), 1 aprendiendo, 2 repaso, 3 reaprendiendo.
    state: Mapped[int] = mapped_column(Integer, default=0)
    step: Mapped[int | None] = mapped_column(Integer, nullable=True)
    stability: Mapped[float | None] = mapped_column(Float, nullable=True)
    difficulty: Mapped[float | None] = mapped_column(Float, nullable=True)
    due: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)
    last_review: Mapped[datetime | None] = mapped_column(UTCDateTime, nullable=True)
    reps: Mapped[int] = mapped_column(Integer, default=0)
    lapses: Mapped[int] = mapped_column(Integer, default=0)

    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow, onupdate=utcnow)

    deck: Mapped[Deck] = relationship(back_populates="cards")
    hooks: Mapped[list[Hook]] = relationship(back_populates="card", cascade="all, delete-orphan")
    reviews: Mapped[list[Review]] = relationship(back_populates="card", cascade="all, delete-orphan")


class Hook(Base):
    """Gancho mnemotécnico: el «asa» de donde tirar para recuperar la respuesta."""

    __tablename__ = "hooks"

    id: Mapped[int] = mapped_column(primary_key=True)
    card_id: Mapped[int] = mapped_column(ForeignKey("cards.id", ondelete="CASCADE"), index=True)
    technique: Mapped[str] = mapped_column(String(30))
    text: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)

    card: Mapped[Card] = relationship(back_populates="hooks")


class Review(Base):
    __tablename__ = "reviews"

    id: Mapped[int] = mapped_column(primary_key=True)
    card_id: Mapped[int] = mapped_column(ForeignKey("cards.id", ondelete="CASCADE"), index=True)
    rating: Mapped[int] = mapped_column(Integer)  # 1 Otra vez · 2 Difícil · 3 Bien · 4 Fácil
    reviewed_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow, index=True)
    duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    state_before: Mapped[int] = mapped_column(Integer)
    stability_after: Mapped[float | None] = mapped_column(Float, nullable=True)
    difficulty_after: Mapped[float | None] = mapped_column(Float, nullable=True)
    due_after: Mapped[datetime] = mapped_column(UTCDateTime)
    typed_answer: Mapped[str | None] = mapped_column(Text, nullable=True)

    card: Mapped[Card] = relationship(back_populates="reviews")


class Palace(Base):
    __tablename__ = "palaces"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(160), unique=True)
    description: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)

    loci: Mapped[list[Locus]] = relationship(
        back_populates="palace", cascade="all, delete-orphan", order_by="Locus.position"
    )


class Locus(Base):
    """Estación del palacio: un lugar concreto + la escena absurda que ancla una tarjeta."""

    __tablename__ = "loci"

    id: Mapped[int] = mapped_column(primary_key=True)
    palace_id: Mapped[int] = mapped_column(ForeignKey("palaces.id", ondelete="CASCADE"), index=True)
    position: Mapped[int] = mapped_column(Integer)
    place: Mapped[str] = mapped_column(String(200))
    scene: Mapped[str] = mapped_column(Text, default="")
    card_id: Mapped[int | None] = mapped_column(ForeignKey("cards.id", ondelete="SET NULL"), nullable=True)

    palace: Mapped[Palace] = relationship(back_populates="loci")
    card: Mapped[Card | None] = relationship()


class TrainingResult(Base):
    __tablename__ = "training_results"

    id: Mapped[int] = mapped_column(primary_key=True)
    game: Mapped[str] = mapped_column(String(30), index=True)  # digitos|sistema_mayor|pares|secuencia
    score: Mapped[int] = mapped_column(Integer)
    level: Mapped[int] = mapped_column(Integer, default=1)
    details: Mapped[dict] = mapped_column(JSON, default=dict)
    played_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow, index=True)
