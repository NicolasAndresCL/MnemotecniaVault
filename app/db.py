"""Engine, sesiones e inicialización de la base de datos (SQLAlchemy 2.x)."""

from __future__ import annotations

import json
from collections.abc import Iterator
from contextlib import contextmanager
from functools import lru_cache

from sqlalchemy import Engine, create_engine, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.config import get_settings


class Base(DeclarativeBase):
    pass


@lru_cache
def get_engine() -> Engine:
    url = get_settings().database_url
    # ensure_ascii=False: las tildes de los tags quedan legibles en la BD.
    kwargs: dict = {"json_serializer": lambda o: json.dumps(o, ensure_ascii=False)}
    if url.startswith("sqlite"):
        kwargs["connect_args"] = {"check_same_thread": False}
        if url in {"sqlite://", "sqlite:///:memory:"}:
            kwargs["poolclass"] = StaticPool  # una sola conexión: la BD en memoria sobrevive
        return create_engine(url, **kwargs)
    return create_engine(url, pool_pre_ping=True, pool_size=5, max_overflow=10, **kwargs)


@lru_cache
def _session_factory() -> sessionmaker[Session]:
    return sessionmaker(bind=get_engine(), expire_on_commit=False)


@contextmanager
def session_scope() -> Iterator[Session]:
    """Una unidad de trabajo: commit si todo sale bien, rollback si algo lanza."""
    session = _session_factory()()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def init_db() -> None:
    """Crea las tablas. En Postgres, bajo un advisory lock: varios workers pueden arrancar a la vez."""
    from app import models  # noqa: F401  (registra los modelos en Base.metadata)

    engine = get_engine()
    with engine.begin() as conn:
        if engine.dialect.name == "postgresql":
            conn.execute(text("SELECT pg_advisory_xact_lock(727274)"))
        Base.metadata.create_all(conn)


def reset_caches() -> None:
    """Para tests: olvida engine y sesiones cacheados (cambió DATABASE_URL)."""
    _session_factory.cache_clear()
    get_engine.cache_clear()
